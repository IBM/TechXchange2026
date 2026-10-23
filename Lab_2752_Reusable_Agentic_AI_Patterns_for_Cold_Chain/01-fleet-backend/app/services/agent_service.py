"""Agent service for watsonx Orchestrate integration"""
import httpx
import uuid
import json
import logging
import sys
import time
import asyncio
from copy import deepcopy
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import BackgroundTasks
from ..models.agent import (
    AgentExecution,
    AgentStatus,
    AgentStatusEnum,
    ExecutionStatusEnum
)
from ..services.truck_service import truck_service
from ..config.settings import get_settings

# Decisions that require external system integration.
# MONITOR and CONTINUE have no downstream action to perform.
_ACTIONABLE_DECISIONS = frozenset({"EMERGENCY_REROUTE", "CONTROLLED_REROUTE", "ABORT"})

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Raised when Decision Agent payload fails schema validation"""
    pass


class AgentService:
    """Service for orchestrating watsonx Orchestrate agents"""
    
    def __init__(self):
        self.execution_history: List[AgentExecution] = []
        self.current_executions: Dict[str, AgentExecution] = {}

        # IAM token management
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[float] = None

        # Notification storage: Dict[truck_id, List[notification_dict]]
        self.notifications: Dict[str, List[Dict[str, Any]]] = {}

        # Shared httpx client for webMethods — reused across calls for connection pooling
        self._wm_client: Optional[httpx.AsyncClient] = None
    
    async def execute_agent_workflow(self, truck_id: str) -> AgentExecution:
        """
        Execute complete agent workflow for a truck.
        Agents execute sequentially: Weather → Station → Route → Decision → Notification
        
        Args:
            truck_id: Truck ID to analyze
            
        Returns:
            AgentExecution with initial status (workflow runs in background)
        """
        # Validate truck exists
        truck = truck_service.get_truck(truck_id)
        if not truck:
            raise ValueError(f"Truck {truck_id} not found")
        
        # Create execution record
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        execution = AgentExecution(
            execution_id=execution_id,
            truck_id=truck_id,
            status=ExecutionStatusEnum.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # Store execution
        self.current_executions[execution_id] = execution
        
        # Start workflow in background (don't await)
        asyncio.create_task(self._run_workflow_background(execution, truck))
        
        # Return immediately so frontend can start polling
        return execution
    
    async def _run_workflow_background(self, execution: AgentExecution, truck: Any):
        """Run the workflow in the background and handle completion"""
        try:
            # Execute agents sequentially
            await self._execute_workflow(execution, truck)
        except Exception as e:
            logger.error(f"Agent workflow failed for truck {execution.truck_id}: {e}")
            execution.status = ExecutionStatusEnum.FAILED
            execution.completed_at = datetime.utcnow()
        
        # Move to history when complete
        self.execution_history.append(execution)
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
        
        # Remove from current executions after a delay (keep it available for final polling)
        await asyncio.sleep(60)  # Keep for 60 seconds after completion
        if execution.execution_id in self.current_executions:
            del self.current_executions[execution.execution_id]
    
    async def _execute_workflow(self, execution: AgentExecution, truck: Any):
        """Execute the agent workflow"""
        try:
            # Step 1: Weather Agent
            execution.agents["weather"].status = AgentStatusEnum.RUNNING
            execution.agents["weather"].started_at = datetime.utcnow()
            
            weather_output = await self._call_weather_agent(truck)
            
            execution.agents["weather"].status = AgentStatusEnum.COMPLETED
            execution.agents["weather"].completed_at = datetime.utcnow()
            execution.agents["weather"].progress = 100
            execution.agents["weather"].output = weather_output
            
            # Step 2: Station Agent
            execution.agents["station"].status = AgentStatusEnum.RUNNING
            execution.agents["station"].started_at = datetime.utcnow()
            
            station_output = await self._call_station_agent(truck, weather_output)
            
            execution.agents["station"].status = AgentStatusEnum.COMPLETED
            execution.agents["station"].completed_at = datetime.utcnow()
            execution.agents["station"].progress = 100
            execution.agents["station"].output = station_output
            
            # Step 3: Route Agent
            execution.agents["route"].status = AgentStatusEnum.RUNNING
            execution.agents["route"].started_at = datetime.utcnow()
            
            route_output = await self._call_route_agent(truck, station_output)
            
            execution.agents["route"].status = AgentStatusEnum.COMPLETED
            execution.agents["route"].completed_at = datetime.utcnow()
            execution.agents["route"].progress = 100
            execution.agents["route"].output = route_output
            
            # Step 4: Decision Agent
            execution.agents["decision"].status = AgentStatusEnum.RUNNING
            execution.agents["decision"].started_at = datetime.utcnow()
            
            decision_output = await self._call_decision_agent(
                truck, weather_output, station_output, route_output
            )
            
            execution.agents["decision"].status = AgentStatusEnum.COMPLETED
            execution.agents["decision"].completed_at = datetime.utcnow()
            execution.agents["decision"].progress = 100
            execution.agents["decision"].output = decision_output
            
            # Apply decision to truck and resolve alerts
            logger.info(f"🔍 CHECKPOINT: About to call _apply_decision_to_truck for truck {truck.truckId}")
            logger.info(f"🔍 decision_output type: {type(decision_output)}, value: {decision_output}")
            await self._apply_decision_to_truck(truck, decision_output)
            logger.info(f"🔍 CHECKPOINT: _apply_decision_to_truck completed for truck {truck.truckId}")

            # Trigger webMethods integration flows (non-blocking — errors stored, never raised)
            await self._trigger_webmethods_integration(execution, truck, decision_output)

            # Step 5: Notification Agent
            execution.agents["notification"].status = AgentStatusEnum.RUNNING
            execution.agents["notification"].started_at = datetime.utcnow()
            
            notification_output = await self._call_notification_agent(
                truck, decision_output
            )
            
            execution.agents["notification"].status = AgentStatusEnum.COMPLETED
            execution.agents["notification"].completed_at = datetime.utcnow()
            execution.agents["notification"].progress = 100
            execution.agents["notification"].output = notification_output
            
            # Mark execution as completed
            execution.status = ExecutionStatusEnum.COMPLETED
            execution.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution.status = ExecutionStatusEnum.FAILED
            execution.completed_at = datetime.utcnow()
            raise
    
    async def _call_weather_agent(self, truck: Any) -> Dict[str, Any]:
        """
        Call Weather Agent via watsonx Orchestrate Chat API with retry logic
        
        Endpoint: POST /v1/orchestrate/{agent_id}/chat/completions
        """
        settings = get_settings()
        if not settings.watsonx_orchestrate.enabled:
            logger.warning("watsonx Orchestrate is disabled, returning mock data")
            return self._mock_weather_output()
        
        # Construct payload
        route_path = []
        if truck.currentTrip and truck.currentTrip.plannedRoute:
            route_path = [
                {
                    "latitude": wp.latitude,
                    "longitude": wp.longitude,
                    "city": wp.city if hasattr(wp, 'city') else None
                }
                for wp in truck.currentTrip.plannedRoute
            ]
        
        payload = {
            "truckId": truck.truckId,
            "currentLocation": {
                "latitude": truck.telemetry.currentLocation.latitude,
                "longitude": truck.telemetry.currentLocation.longitude
            },
            "destination": {
                "latitude": truck.currentTrip.destination.latitude,
                "longitude": truck.currentTrip.destination.longitude
            },
            "routePath": route_path
        }
        
        # Retry logic: 3 total attempts with exponential backoff
        max_attempts = 3
        last_exception: Exception | None = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Weather Agent call attempt {attempt}/{max_attempts}")
                
                result = await self._call_watsonx_agent(
                    agent_id=settings.watsonx_orchestrate.agent_weather,
                    payload=payload
                )
                
                logger.info(f"Weather Agent call succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.error(f"Weather Agent call attempt {attempt} failed: {e}")
                
                if attempt < max_attempts:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
        
        # All attempts exhausted
        logger.error(f"Weather Agent failed after {max_attempts} attempts")
        raise Exception(f"Weather Agent failed after {max_attempts} attempts. Last error: {str(last_exception)}")
    
    async def _call_station_agent(self, truck: Any, weather_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Station Agent via watsonx Orchestrate Chat API with retry logic
        
        Endpoint: POST /v1/orchestrate/{agent_id}/chat/completions
        """
        settings = get_settings()
        if not settings.watsonx_orchestrate.enabled:
            logger.warning("watsonx Orchestrate is disabled, returning mock data")
            return self._mock_station_output()
        
        # Determine search strategy based on weather
        search_strategy = "alternative_locations" if weather_output.get("severeWeatherDetected", False) else "along_planned_route"
        
        # Construct payload according to API guide schema
        planned_route = []
        if truck.currentTrip and truck.currentTrip.plannedRoute:
            planned_route = [
                {
                    "latitude": wp.latitude,
                    "longitude": wp.longitude,
                    "city": wp.city if hasattr(wp, 'city') else None,
                    "highway": wp.highway if hasattr(wp, 'highway') else None
                }
                for wp in truck.currentTrip.plannedRoute
            ]
        
        payload = {
            "truckId": truck.truckId,
            "searchRadius": 50.0,  # km
            "searchStrategy": search_strategy,
            "plannedRoute": planned_route,
            "requiredCapabilities": ["emergencyCooling", "tire_repair"],
            "cargoType": "perishable_food"
        }
        
        # Retry logic: 3 total attempts with exponential backoff
        max_attempts = 3
        last_exception: Exception | None = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Station Agent call attempt {attempt}/{max_attempts}")
                
                result = await self._call_watsonx_agent(
                    agent_id=settings.watsonx_orchestrate.agent_station,
                    payload=payload
                )
                
                logger.info(f"Station Agent call succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.error(f"Station Agent call attempt {attempt} failed: {e}")
                
                if attempt < max_attempts:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
        
        # All attempts exhausted
        logger.error(f"Station Agent failed after {max_attempts} attempts")
        raise Exception(f"Station Agent failed after {max_attempts} attempts. Last error: {str(last_exception)}")
    
    async def _call_route_agent(self, truck: Any, station_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Route Agent via watsonx Orchestrate Chat API with retry logic
        
        Endpoint: POST /v1/orchestrate/{agent_id}/chat/completions
        """
        settings = get_settings()
        if not settings.watsonx_orchestrate.enabled:
            logger.warning("watsonx Orchestrate is disabled, returning mock data")
            return self._mock_route_output()
        
        # Extract facilities from station agent output (API returns "facilities" not "stations")
        facilities = station_output.get("facilities", [])
        
        # Construct payload according to API guide schema
        payload = {
            "truckId": truck.truckId,
            "currentLocation": {
                "latitude": truck.telemetry.currentLocation.latitude,
                "longitude": truck.telemetry.currentLocation.longitude
            },
            "originalDestination": {
                "latitude": truck.currentTrip.destination.latitude,
                "longitude": truck.currentTrip.destination.longitude,
                "name": truck.currentTrip.destination.name if hasattr(truck.currentTrip.destination, 'name') else "Destination"
            },
            "facilities": facilities,
            "cargoType": "perishable_food"
        }
        
        # Retry logic: 3 total attempts with exponential backoff
        max_attempts = 3
        last_exception: Exception | None = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Route Agent call attempt {attempt}/{max_attempts}")
                
                result = await self._call_watsonx_agent(
                    agent_id=settings.watsonx_orchestrate.agent_route,
                    payload=payload
                )
                
                logger.info(f"Route Agent call succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.error(f"Route Agent call attempt {attempt} failed: {e}")
                
                if attempt < max_attempts:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
        
        # All attempts exhausted
        logger.error(f"Route Agent failed after {max_attempts} attempts")
        raise Exception(f"Route Agent failed after {max_attempts} attempts. Last error: {str(last_exception)}")
        
    def _auto_correct_decision_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically correct Decision Agent payload to match required schema.
        Ensures all required fields are present with proper structure and defaults.
        
        IMPORTANT: Uses deepcopy to avoid modifying the original payload data,
        which would corrupt the agent outputs stored in execution.agents[].output
        
        Args:
            payload: Original payload that may have schema issues
            
        Returns:
            Corrected payload that matches Decision Agent tool schema
        """
        corrected = deepcopy(payload)
        
        # Ensure top-level required fields
        if "truckId" not in corrected:
            corrected["truckId"] = "UNKNOWN"
        if "incidentId" not in corrected:
            corrected["incidentId"] = f"incident-{datetime.utcnow().strftime('%Y%m%d')}-001"
        
        # Ensure telemetry structure
        if "telemetry" not in corrected or not isinstance(corrected["telemetry"], dict):
            corrected["telemetry"] = {}
        
        telemetry = corrected["telemetry"]
        if "temperature" not in telemetry:
            telemetry["temperature"] = 0.0
        if "coolantStatus" not in telemetry:
            telemetry["coolantStatus"] = "UNKNOWN"
        if "location" not in telemetry or not isinstance(telemetry["location"], dict):
            telemetry["location"] = {"latitude": 0.0, "longitude": 0.0}
        else:
            if "latitude" not in telemetry["location"]:
                telemetry["location"]["latitude"] = 0.0
            if "longitude" not in telemetry["location"]:
                telemetry["location"]["longitude"] = 0.0
        
        # Ensure cargo structure
        if "cargo" not in corrected or not isinstance(corrected["cargo"], dict):
            corrected["cargo"] = {}
        
        cargo = corrected["cargo"]
        if "value" not in cargo:
            cargo["value"] = 200000
        if "criticalThreshold" not in cargo:
            cargo["criticalThreshold"] = -10
        if "timeToSpoilage" not in cargo:
            cargo["timeToSpoilage"] = 120
        
        # Ensure originalPlan structure
        if "originalPlan" not in corrected or not isinstance(corrected["originalPlan"], dict):
            corrected["originalPlan"] = {}
        
        original_plan = corrected["originalPlan"]
        if "destination" not in original_plan:
            original_plan["destination"] = "Unknown Destination"
        if "estimatedArrival" not in original_plan:
            original_plan["estimatedArrival"] = datetime.utcnow().isoformat()
        
        # Auto-correct weatherAnalysis structure
        if "weatherAnalysis" not in corrected or not isinstance(corrected["weatherAnalysis"], dict):
            corrected["weatherAnalysis"] = {}
        
        weather = corrected["weatherAnalysis"]
        if "severeWeatherDetected" not in weather:
            weather["severeWeatherDetected"] = False
        if "overallWeatherRisk" not in weather:
            weather["overallWeatherRisk"] = 0
        if "totalDelayMinutes" not in weather:
            weather["totalDelayMinutes"] = 0
        # Only add segments if completely missing
        if "segments" not in weather:
            weather["segments"] = []
        # If segments exists but is not a list, try to preserve it
        elif not isinstance(weather["segments"], list):
            weather["segments"] = [weather["segments"]] if weather["segments"] else []
        
        # Ensure each weather segment has required fields (only add if missing)
        for segment in weather["segments"]:
            if not isinstance(segment, dict):
                continue
            # Only add fields if they don't exist - preserve existing data
            if "location" not in segment:
                segment["location"] = "Unknown"
            if "condition" not in segment:
                segment["condition"] = "Unknown"
            if "risk" not in segment:
                segment["risk"] = 0
            if "delayMinutes" not in segment:
                segment["delayMinutes"] = 0
        
        # Auto-correct stationAnalysis structure
        if "stationAnalysis" not in corrected or not isinstance(corrected["stationAnalysis"], dict):
            corrected["stationAnalysis"] = {}
        
        station = corrected["stationAnalysis"]
        # Only add facilities if completely missing
        if "facilities" not in station:
            station["facilities"] = []
        # If facilities exists but is not a list, try to preserve it
        elif not isinstance(station["facilities"], list):
            station["facilities"] = [station["facilities"]] if station["facilities"] else []
        
        # Only add searchStrategyUsed if missing
        if "searchStrategyUsed" not in station:
            station["searchStrategyUsed"] = "along_planned_route"
        
        # Ensure each facility has required fields (only add if missing)
        for facility in station["facilities"]:
            if not isinstance(facility, dict):
                continue
            # Only add fields if they don't exist - preserve existing data
            if "name" not in facility:
                facility["name"] = "Unknown Facility"
            if "latitude" not in facility:
                facility["latitude"] = 0.0
            if "longitude" not in facility:
                facility["longitude"] = 0.0
            if "distance" not in facility:
                facility["distance"] = 0.0
            # Only add capabilities if completely missing - don't overwrite existing data
            if "capabilities" not in facility:
                facility["capabilities"] = []
            # If capabilities exists but is not a list, try to preserve it
            elif not isinstance(facility["capabilities"], list):
                facility["capabilities"] = [facility["capabilities"]] if facility["capabilities"] else []
        
        # Auto-correct routeAnalysis structure
        if "routeAnalysis" not in corrected or not isinstance(corrected["routeAnalysis"], dict):
            corrected["routeAnalysis"] = {}
        
        route = corrected["routeAnalysis"]
        # Only add routes if completely missing
        if "routes" not in route:
            route["routes"] = []
        # If routes exists but is not a list, try to preserve it
        elif not isinstance(route["routes"], list):
            route["routes"] = [route["routes"]] if route["routes"] else []
        
        # Ensure each route has required fields (only add if missing)
        for route_item in route["routes"]:
            if not isinstance(route_item, dict):
                continue
            # Only add fields if they don't exist - preserve existing data
            if "routeId" not in route_item:
                route_item["routeId"] = "route-1"
            # Only add waypoints if completely missing
            if "waypoints" not in route_item:
                route_item["waypoints"] = []
            # If waypoints exists but is not a list, try to preserve it
            elif not isinstance(route_item["waypoints"], list):
                route_item["waypoints"] = [route_item["waypoints"]] if route_item["waypoints"] else []
            if "totalDistance" not in route_item:
                route_item["totalDistance"] = 0.0
            if "estimatedDuration" not in route_item:
                route_item["estimatedDuration"] = 0
            if "includesServiceStop" not in route_item:
                route_item["includesServiceStop"] = False
        
        logger.info("Decision Agent payload auto-corrected successfully")
        return corrected
    
    async def _call_decision_agent(
        self,
        truck: Any,
        weather_output: Dict[str, Any],
        station_output: Dict[str, Any],
        route_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Decision Agent via watsonx Orchestrate Chat API with automatic
        schema correction and retry logic.
        
        Endpoint: POST /v1/orchestrate/{agent_id}/chat/completions
        """
        settings = get_settings()
        if not settings.watsonx_orchestrate.enabled:
            logger.warning("watsonx Orchestrate is disabled, returning mock data")
            return self._mock_decision_output()
        
        # Log actual agent outputs for debugging
        logger.info("=" * 80)
        logger.info("DECISION AGENT - RECEIVED RAW INPUTS:")
        logger.info(f"Weather Output: {json.dumps(weather_output, indent=2)}")
        logger.info(f"Station Output: {json.dumps(station_output, indent=2)}")
        logger.info(f"Route Output: {json.dumps(route_output, indent=2)}")
        logger.info("=" * 80)
        
        # Construct payload with raw agent outputs (no transformation)
        # Let watsonx Orchestrate handle the conversion to Pydantic models
        payload = {
            "truckId": truck.truckId,
            "incidentId": f"incident-{datetime.utcnow().strftime('%Y%m%d')}-001",
            "telemetry": {
                "temperature": truck.telemetry.temperature,
                "coolantStatus": truck.telemetry.coolantStatus,
                "location": {
                    "latitude": truck.telemetry.currentLocation.latitude,
                    "longitude": truck.telemetry.currentLocation.longitude
                }
            },
            "cargo": {
                "value": truck.cargo.value if hasattr(truck.cargo, 'value') else 200000,
                "criticalThreshold": truck.cargo.criticalThreshold if hasattr(truck.cargo, 'criticalThreshold') else -10,
                "timeToSpoilage": 120  # minutes
            },
            "originalPlan": {
                "destination": truck.currentTrip.destination.name if hasattr(truck.currentTrip.destination, 'name') else "Destination",
                "estimatedArrival": truck.currentTrip.estimatedArrival.isoformat() if hasattr(truck.currentTrip, 'estimatedArrival') else datetime.utcnow().isoformat()
            },
            "weatherAnalysis": weather_output,  # Pass raw output
            "stationAnalysis": station_output,  # Pass raw output
            "routeAnalysis": route_output       # Pass raw output
        }
        
        logger.info("Decision Agent Payload (with raw agent outputs):")
        logger.info(json.dumps(payload, indent=2))
        logger.info("=" * 80)
        
        # Auto-correct payload to ensure all required fields are present with defaults
        corrected_payload = self._auto_correct_decision_payload(payload)
        
        logger.info("Decision Agent Corrected Payload Being Sent:")
        logger.info(json.dumps(corrected_payload, indent=2))
        
        # Retry logic: 3 total attempts with exponential backoff.
        # Hard outer timeout of 90 s keeps the workflow from blocking indefinitely
        # when the watsonx Orchestrate endpoint is slow or unreachable.
        max_attempts = 3
        last_exception: Exception | None = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Decision Agent call attempt {attempt}/{max_attempts}")
                
                # Call agent with corrected payload, requiring valid JSON response
                result = await self._call_watsonx_agent(
                    agent_id=settings.watsonx_orchestrate.agent_decision,
                    payload=corrected_payload,
                    require_json=True  # Enable retry on invalid JSON
                )
                
                logger.info(f"Decision Agent call succeeded on attempt {attempt}")
                return result
                
            except (json.JSONDecodeError, Exception) as e:
                last_exception = e
                error_type = "Invalid JSON response" if isinstance(e, json.JSONDecodeError) else "Error"
                logger.error(f"Decision Agent call attempt {attempt} failed: {error_type} - {e}")
                
                if attempt < max_attempts:
                    # Exponential backoff: 2^attempt seconds (2s, 4s)
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying Decision Agent in {wait_time} seconds with same payload...")
                    await asyncio.sleep(wait_time)
                    continue
        
        # All attempts exhausted - raise error
        logger.error(f"Decision Agent failed after {max_attempts} attempts")
        raise SchemaValidationError(
            f"Decision Agent failed after {max_attempts} attempts. "
            f"Last error: {str(last_exception)}"
        )
    
    async def _call_notification_agent(
        self,
        truck: Any,
        decision_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Notification Agent via watsonx Orchestrate Chat API with retry logic.
        Sends WhatsApp notification about the decision to the driver.
        
        Endpoint: POST /v1/orchestrate/{agent_id}/chat/completions
        """
        settings = get_settings()
        if not settings.watsonx_orchestrate.enabled:
            logger.warning("watsonx Orchestrate is disabled, returning mock data")
            return self._mock_notification_output()
        
        # Construct payload according to notification agent schema
        # The agent expects: truckId, decisionOutput (complete decision JSON), and optional driverName
        payload = {
            "truckId": truck.truckId,
            "decisionOutput": decision_output,  # Pass complete decision output as-is
            "driverName": "Loco Pilot"  # Default driver name
        }
        
        logger.info("Notification Agent Payload:")
        logger.info(json.dumps(payload, indent=2))
        
        # Retry logic: 3 total attempts with exponential backoff
        max_attempts = 3
        last_exception: Exception | None = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Notification Agent call attempt {attempt}/{max_attempts}")
                
                result = await self._call_watsonx_agent(
                    agent_id=settings.watsonx_orchestrate.agent_notification,
                    payload=payload,
                    require_json=False  # Notification agent returns simple confirmation
                )

                # Detect soft-error responses (agent ran but returned an error payload).
                # e.g. {"notificationSent": false, "status": "ERROR", "error": "...connection not configured..."}
                result_status = result.get("status", "") if isinstance(result, dict) else ""
                if result_status == "ERROR" or (isinstance(result, dict) and result.get("notificationSent") is False and result.get("error")):
                    error_msg = result.get("error", "Notification Agent returned error status")
                    logger.warning(f"Notification Agent soft-error (attempt {attempt}): {error_msg}")
                    # Don't retry connection-config errors — they won't fix themselves
                    if "not configured" in error_msg or "connection" in error_msg.lower():
                        logger.warning("Orchestrate connection misconfiguration detected — falling back to mock notification")
                        mock = self._mock_notification_output()
                        mock["_orchestrate_error"] = error_msg
                        self._store_notification(truck.truckId, decision_output, mock)
                        return mock
                    last_exception = Exception(error_msg)
                    if attempt < max_attempts:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                        continue
                    break

                logger.info(f"Notification Agent call succeeded on attempt {attempt}")
                self._store_notification(truck.truckId, decision_output, result)
                return result
                
            except Exception as e:
                last_exception = e
                logger.error(f"Notification Agent call attempt {attempt} failed: {e}")
                
                if attempt < max_attempts:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
        
        # All attempts exhausted — fall back to mock so the workflow completes cleanly
        logger.error(f"Notification Agent failed after {max_attempts} attempts — using mock output")
        mock = self._mock_notification_output()
        mock["_orchestrate_error"] = str(last_exception)
        self._store_notification(truck.truckId, decision_output, mock)
        return mock
    
    def _store_notification(self, truck_id: str, decision_output: Dict[str, Any], notification_result: Dict[str, Any]):
        """Store notification for later retrieval"""
        if truck_id not in self.notifications:
            self.notifications[truck_id] = []
        
        notification = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "truckId": truck_id,
            "decision": decision_output.get("decision", "UNKNOWN"),
            "urgency": decision_output.get("urgency", "UNKNOWN"),
            "message": decision_output.get("recommendation", "Decision applied"),
            "facility": decision_output.get("selectedFacility", {}).get("name", None),
            "notificationResult": notification_result
        }
        
        self.notifications[truck_id].append(notification)
        
        # Keep only last 10 notifications per truck
        if len(self.notifications[truck_id]) > 10:
            self.notifications[truck_id] = self.notifications[truck_id][-10:]
        
        logger.info(f"Stored notification for truck {truck_id}: {notification['decision']}")
    
    def get_notifications(self, truck_id: str) -> List[Dict[str, Any]]:
        """Get all notifications for a truck"""
        return self.notifications.get(truck_id, [])
    
    def _generate_iam_token(self) -> Dict[str, Any]:
        """
        Generate IAM access token from API key.
        Based on test_agents_interactive.py implementation.
        """
        logger.info("Generating IAM access token...")
        
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": get_settings().watsonx_orchestrate.api_key
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://iam.cloud.ibm.com/identity/token",
                    data=data,
                    headers=headers
                )
                response.raise_for_status()
                
                token_data = response.json()
                logger.info(f"IAM token generated (expires in {token_data['expires_in']}s)")
                return token_data
                
        except Exception as e:
            logger.error(f"Error generating IAM token: {e}")
            raise
    
    def _ensure_valid_token(self):
        """Ensure we have a valid IAM access token."""
        if self.access_token and self.token_expiry:
            time_until_expiry = self.token_expiry - time.time()
            if time_until_expiry > 300:  # 5 minute buffer
                return
        
        # Generate new token
        token_data = self._generate_iam_token()
        self.access_token = token_data["access_token"]
        self.token_expiry = time.time() + token_data["expires_in"]
    
    async def _call_watsonx_agent(
        self,
        agent_id: str,
        payload: Dict[str, Any],
        thread_id: Optional[str] = None,
        require_json: bool = True
    ) -> Dict[str, Any]:
        """
        Call a watsonx Orchestrate agent using the Chat with Agents API
        
        Args:
            agent_id: The unique identifier of the agent
            payload: Agent-specific payload
            thread_id: Optional thread ID for conversation context
            require_json: If True, raise exception on invalid JSON response (enables retry)
            
        Returns:
            Agent response from choices[0].message.content
            
        Raises:
            json.JSONDecodeError: If require_json=True and response is not valid JSON
        """
        # Ensure we have a valid IAM token
        self._ensure_valid_token()
        
        settings = get_settings()
        url = f"{settings.watsonx_orchestrate.url}/v1/orchestrate/{agent_id}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",  # Use IAM token, not API key
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add thread ID if provided
        if thread_id:
            headers["X-IBM-THREAD-ID"] = thread_id
        
        # Construct request body
        # CRITICAL: content must be a JSON STRING, not an object
        # This is confirmed by test_agents_interactive.py and orchestrate_api/orchestrate_client.py
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(payload)  # Convert payload to JSON string
                }
            ],
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=settings.watsonx_orchestrate.timeout) as client:
            response = await client.post(url, headers=headers, json=request_body)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract agent output from response
            # The content is a JSON string, so parse it
            content = result["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                # Log the invalid response
                logger.warning(f"Agent response content is not valid JSON: {content[:200]}")
                
                # If JSON is required, raise exception to trigger retry
                if require_json:
                    raise json.JSONDecodeError(
                        f"Agent returned invalid JSON response: {content[:100]}",
                        content,
                        0
                    )
                
                # Otherwise return as-is for backward compatibility
                return {"raw_content": content}
    
    # ------------------------------------------------------------------
    # webMethods integration
    # ------------------------------------------------------------------

    async def _get_wm_client(self, timeout: int) -> httpx.AsyncClient:
        """Return the shared webMethods httpx client, creating it if needed.

        Reusing a single AsyncClient across calls enables HTTP connection
        pooling and avoids a fresh TLS handshake on every integration trigger.
        """
        if self._wm_client is None or self._wm_client.is_closed:
            self._wm_client = httpx.AsyncClient(timeout=timeout)
        return self._wm_client

    async def _trigger_webmethods_integration(
        self,
        execution: AgentExecution,
        truck: Any,
        decision_output: Dict[str, Any],
    ) -> None:
        """Fire webMethods integration flows after a decision is applied.

        Only fires for actionable decisions (EMERGENCY_REROUTE, CONTROLLED_REROUTE,
        ABORT). MONITOR and CONTINUE are skipped — there is nothing to book, hold,
        or flag for those outcomes.

        Uses a shared httpx.AsyncClient for connection pooling, retries up to
        3 times with exponential backoff, and correlates the call with the
        execution_id so webMethods logs and fleetops-backend history share the
        same reference. Errors never propagate — they are stored on the execution
        object so the dashboard can surface them.
        """
        settings = get_settings()
        wm = settings.webmethods

        if not wm.enabled:
            logger.info("webMethods integration disabled — skipping")
            return

        if not wm.url or not wm.api_key:
            logger.warning("webMethods enabled but URL/API key not configured — skipping")
            execution.integration_error = "webMethods URL or API key not configured"
            return

        # #1 — Gate: only fire for decisions that require downstream action
        decision = decision_output.get("decision", "MONITOR").upper()
        if decision not in _ACTIONABLE_DECISIONS:
            logger.info(
                f"Skipping webMethods for truck {truck.truckId} — "
                f"decision={decision!r} requires no external system action"
            )
            return

        trip_id      = truck.currentTrip.tripId if truck.currentTrip else f"TRIP-{truck.truckId}"
        shipment_id  = f"SHIP-{truck.truckId}-{execution.execution_id[-6:]}"
        product_id   = f"PROD-{truck.truckId}"
        batch_number = f"BATCH-{datetime.utcnow().strftime('%Y-%m')}-001"

        # Build cargo dict with the fields the webMethods flow input document expects:
        # cargo.type, cargo.shipmentId, cargo.productId, cargo.batchNumber, cargo.tripId
        cargo_dict = {
            "type":        truck.cargo.type if truck.cargo else "PHARMACEUTICAL",
            "shipmentId":  shipment_id,
            "productId":   product_id,
            "batchNumber": batch_number,
            "tripId":      trip_id,
        }

        # Build telemetry dict with the fields the QMS deviation flow expects:
        # telemetry.temperature, telemetry.thresholdMin, telemetry.thresholdMax,
        # telemetry.timestamp, telemetry.location, telemetry.coolantStatus
        loc = {}
        if truck.telemetry and truck.telemetry.currentLocation:
            loc = truck.telemetry.currentLocation.dict() \
                if hasattr(truck.telemetry.currentLocation, "dict") \
                else {"latitude": getattr(truck.telemetry.currentLocation, "latitude", 0),
                      "longitude": getattr(truck.telemetry.currentLocation, "longitude", 0)}
        telemetry_dict = {
            "temperature":   truck.telemetry.temperature if truck.telemetry else 0,
            "thresholdMin":  truck.cargo.criticalThreshold if truck.cargo else -20,
            "thresholdMax":  -15,
            "timestamp":     datetime.utcnow().isoformat() + "Z",
            "location":      f"{loc.get('latitude', 0):.2f}N {loc.get('longitude', 0):.2f}E",
            "coolantStatus": truck.telemetry.coolantStatus if truck.telemetry else "UNKNOWN",
        }

        # Build selectedFacility with the fields the bay-booking flow expects:
        # selectedFacility.stationId, selectedFacility.name, selectedFacility.serviceType
        raw_facility = decision_output.get("selectedFacility") or {}
        selected_facility = {
            "stationId":   raw_facility.get("id") or raw_facility.get("stationId", ""),
            "name":        raw_facility.get("name", ""),
            "serviceType": raw_facility.get("serviceType", "EMERGENCY_COLD_STORAGE"),
        }

        # Build selectedRoute with the fields the ERP hold flow expects:
        # selectedRoute.arrivalTime, selectedRoute.originalETA, selectedRoute.estimatedDelayMinutes
        raw_route = decision_output.get("selectedRoute") or {}
        original_eta = (
            truck.currentTrip.estimatedArrival.isoformat() + "Z"
            if truck.currentTrip and truck.currentTrip.estimatedArrival
            else datetime.utcnow().isoformat() + "Z"
        )
        selected_route = {
            "arrivalTime":           raw_route.get("arrivalTime", original_eta),
            "originalETA":           original_eta,
            "estimatedDelayMinutes": raw_route.get("estimatedDelayMinutes", 90),
        }

        payload = {
            "truckId": truck.truckId,
            # #7 — Use execution_id so webMethods logs and fleetops history share the same key
            "incidentId": execution.execution_id,
            "decision": decision,
            "urgency": decision_output.get("urgency", "LOW"),
            "riskScore": decision_output.get("riskScore", 0),
            "selectedFacility": selected_facility,
            "selectedRoute": selected_route,
            "financialAnalysis": decision_output.get("financialAnalysis"),
            "telemetry": telemetry_dict,
            "cargo": cargo_dict,
        }

        # WEBMETHODS_URL is the full invocation URL — do not append any path
        url = wm.url.rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "X-INSTANCE-API-KEY": wm.api_key,
        }

        # #4 — Retry up to 3 attempts with exponential backoff
        max_attempts = 3
        last_error: Optional[str] = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    f"Triggering webMethods for truck {truck.truckId} "
                    f"decision={decision!r} attempt={attempt}/{max_attempts}"
                )
                # #3 — Shared client (connection pooling / TLS reuse)
                client = await self._get_wm_client(wm.timeout)
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                execution.integration_results = response.json()
                logger.info(
                    f"webMethods integration succeeded for truck {truck.truckId} "
                    f"on attempt {attempt}"
                )
                sys.stdout.flush()

                # #2 — Persist integration result so it survives restarts
                await self._persist_integration_result(execution)
                return

            except httpx.HTTPStatusError as exc:
                last_error = (
                    f"webMethods returned HTTP {exc.response.status_code}: "
                    f"{exc.response.text[:200]}"
                )
                logger.warning(
                    f"webMethods attempt {attempt} failed for truck {truck.truckId}: {last_error}"
                )
                # 4xx errors are not retryable (bad payload / auth)
                if exc.response.status_code < 500:
                    break

            except Exception as exc:
                last_error = f"webMethods unreachable: {exc}"
                logger.warning(
                    f"webMethods attempt {attempt} failed for truck {truck.truckId}: {last_error}"
                )

            if attempt < max_attempts:
                wait = 2 ** attempt
                logger.info(f"Retrying webMethods in {wait}s...")
                await asyncio.sleep(wait)

        # All attempts exhausted — store error, never raise
        execution.integration_error = last_error
        sys.stdout.flush()

    async def _persist_integration_result(self, execution: AgentExecution) -> None:
        """Write integration result to the persistence layer so it survives restarts.

        Uses the injection pattern established by persistence.py — only writes
        when persistence is enabled; silently skips otherwise.
        """
        try:
            from ..services.persistence_service import get_persistence_service
            svc = get_persistence_service()
            if svc.enabled:
                await svc.save_integration_result(execution)
        except Exception as exc:
            # Persistence failure must never block the main workflow
            logger.warning(f"Could not persist integration result: {exc}")

    def get_agent_status(self, execution_id: str) -> Optional[AgentExecution]:
        """Get current status of agent execution"""
        return self.current_executions.get(execution_id)
    
    def get_execution_history(self, truck_id: Optional[str] = None, limit: int = 10) -> List[AgentExecution]:
        """Get historical agent executions"""
        if truck_id:
            filtered = [e for e in self.execution_history if e.truck_id == truck_id]
            return filtered[-limit:]
        return self.execution_history[-limit:]
    
    # Mock data methods for testing without watsonx Orchestrate
    def _mock_weather_output(self) -> Dict[str, Any]:
        """Mock weather agent output"""
        return {
            "severeWeatherDetected": False,
            "overallWeatherRisk": 15,
            "weatherAlongRoute": [
                {"location": "Current", "condition": "Clear", "risk": 10}
            ]
        }
    
    def _mock_station_output(self) -> Dict[str, Any]:
        """Mock station agent output"""
        return {
            "stations": [
                {
                    "name": "Service Station A",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "distance": 25.5
                }
            ]
        }
    
    def _mock_route_output(self) -> Dict[str, Any]:
        """Mock route agent output"""
        return {
            "recommendedRoute": [
                {"latitude": 40.7128, "longitude": -74.0060, "city": "New York"}
            ],
            "totalDistance": 150.5,
            "estimatedTime": 180
        }
    
    def _mock_decision_output(self) -> Dict[str, Any]:
        """Mock decision agent output — matches real Decision Agent schema.

        Returns EMERGENCY_REROUTE so that mock-mode testing exercises the full
        webMethods payload path including selectedFacility and selectedRoute.
        """
        return {
            "decision": "EMERGENCY_REROUTE",
            "urgency": "HIGH",
            "riskScore": 72,
            "selectedFacility": {
                "stationId": "station-mock-001",
                "name": "Mock Cold Storage",
                "serviceType": "emergencyCooling"
            },
            "selectedRoute": {
                "arrivalTime": "2026-07-15T10:30:00Z",
                "originalETA": "2026-07-15T14:00:00Z",
                "estimatedDelayMinutes": 90
            },
            "financialAnalysis": {
                "cargoValueAtRisk": 200000
            },
            "recommendation": "Reroute immediately due to simulated coolant failure"
        }
    def _mock_notification_output(self) -> Dict[str, Any]:
        """Mock notification agent output"""
        return {
            "notificationSent": True,
            "status": "SUCCESS",
            "message": "Mock WhatsApp notification sent to driver",
            "messageSid": "SM_MOCK_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "timestamp": datetime.now().isoformat(),
            "error": None
        }
    
    
    async def _apply_decision_to_truck(self, truck: Any, decision_output: Dict[str, Any]):
        """
        Apply the decision agent's recommendation to the truck and resolve related alerts.
        
        This method:
        1. Extracts the decision type (EMERGENCY_REROUTE, CONTROLLED_REROUTE, CONTINUE, ABORT)
        2. Updates the truck's status and route if needed
        3. Resolves all active alerts for the truck
        
        Args:
            truck: The truck object
            decision_output: Output from the decision agent containing decision and recommendation
        """
        try:
            # Extract decision from decision output (uppercase values like EMERGENCY_REROUTE)
            decision = decision_output.get("decision", "")
            if isinstance(decision, str):
                decision = decision.upper()
            else:
                logger.warning(f"Decision field is not a string: {type(decision)}, value: {decision}")
                decision = ""
            
            truck_id = truck.truckId
            urgency = decision_output.get("urgency", "UNKNOWN")
            
            logger.info(f"Applying decision '{decision}' (urgency: {urgency}) to truck {truck_id}")
            logger.info(f"Full decision output: {json.dumps(decision_output, indent=2)}")
            
            # Import simulation_engine here to avoid circular import
            from ..services.simulation_engine import simulation_engine
            
            # Prepare truck update based on decision
            update_data = {}
            
            if decision == "CONTINUE":
                # Continue on current route - just update status to normal
                update_data["status"] = "ACTIVE"
                logger.info(f"Truck {truck_id}: Continuing on current route")
                
            elif decision in ["EMERGENCY_REROUTE", "CONTROLLED_REROUTE"]:
                # Reroute to alternative facility/route
                update_data["status"] = "DIVERTED"
                
                # Extract selected route and facility information
                selected_route = decision_output.get("selectedRoute", {})
                selected_facility = decision_output.get("selectedFacility", {})
                
                logger.info(f"Truck {truck_id}: Rerouting to facility {selected_facility.get('name', 'Unknown')}")
                logger.info(f"Selected route: {selected_route.get('name', 'Unknown')}, ETA: {selected_route.get('arrivalTime', 'Unknown')}")
                
                # Get destination name and route ID from decision agent's selectedRoute
                destination_name = selected_route.get("destination", "Unknown Destination")
                route_id = selected_route.get("routeId")
                
                # Try to get waypoints from selectedRoute first
                waypoints = selected_route.get("waypoints", [])
                
                # If waypoints not in selectedRoute, look them up from route agent output using routeId
                if (not waypoints or len(waypoints) == 0) and route_id:
                    logger.info(f"Truck {truck_id}: Waypoints not in selectedRoute, looking up route {route_id} from execution history")
                    
                    # Get the execution from current_executions to access route agent output
                    execution = None
                    for exec_id, exec_obj in self.current_executions.items():
                        if exec_obj.truck_id == truck_id:
                            execution = exec_obj
                            break
                    
                    if execution and execution.agents.get("route") and execution.agents["route"].output:
                        route_output = execution.agents["route"].output
                        routes = route_output.get("routes", [])
                        
                        # Find the matching route by routeId
                        for route in routes:
                            if route.get("routeId") == route_id:
                                waypoints = route.get("waypoints", [])
                                logger.info(f"Truck {truck_id}: Found {len(waypoints)} waypoints from route agent output for route {route_id}")
                                break
                    
                    if not waypoints or len(waypoints) == 0:
                        logger.warning(f"Truck {truck_id}: Could not find waypoints for route {route_id} in execution history")
                if waypoints and len(waypoints) > 0:
                    from ..models.route import RouteWaypoint, Location
                    
                    # Convert waypoints to proper format
                    new_waypoints = []
                    for wp in waypoints:
                        if isinstance(wp, dict):
                            waypoint = RouteWaypoint(
                                latitude=wp.get("latitude", 0.0),
                                longitude=wp.get("longitude", 0.0),
                                city=wp.get("city", ""),
                                highway=wp.get("highway", "")
                            )
                            new_waypoints.append(waypoint)
                    
                    # Update truck's planned route - preserve existing currentTrip fields
                    if new_waypoints:
                        # Get existing currentTrip to preserve all fields
                        existing_trip = truck.currentTrip
                        
                        # Create new destination using the last waypoint coordinates and destination name from decision agent
                        last_wp = waypoints[-1]
                        new_destination = Location(
                            latitude=last_wp.get("latitude", 0.0),
                            longitude=last_wp.get("longitude", 0.0),
                            name=destination_name,  # Use destination name from decision agent
                            address=last_wp.get("city", "")
                        )
                        logger.info(f"Truck {truck_id}: Updated destination to: {new_destination.name} at ({new_destination.latitude}, {new_destination.longitude})")
                        
                        # Create complete currentTrip dict preserving all existing fields
                        update_data["currentTrip"] = {
                            "tripId": existing_trip.tripId,
                            "origin": existing_trip.origin,
                            "destination": new_destination,  # Updated destination
                            "plannedRoute": new_waypoints,  # Updated route with waypoints
                            "estimatedArrival": existing_trip.estimatedArrival,
                            "currentWaypointIndex": existing_trip.currentWaypointIndex,
                            "distanceTraveled": existing_trip.distanceTraveled,
                            "distanceRemaining": existing_trip.distanceRemaining
                        }
                        
                        logger.info(f"Truck {truck_id}: Updated route with {len(new_waypoints)} waypoints and destination: {new_destination.name}")
                else:
                    logger.warning(f"Truck {truck_id}: No waypoints found, only updating status to DIVERTED")
                
            elif decision == "ABORT":
                # Abort mission - stop immediately
                update_data["status"] = "STOPPED"
                logger.info(f"Truck {truck_id}: Mission aborted, stopping immediately")
            
            else:
                # Unknown decision type - log warning but don't fail
                logger.warning(f"Unknown decision type '{decision}' for truck {truck_id}, defaulting to ACTIVE status")
                update_data["status"] = "ACTIVE"
            
            # Apply truck updates if any
            if update_data:
                # If diverting, save the original route first
                if update_data.get('status') == 'DIVERTED' and not truck.originalRoute:
                    logger.info(f"Truck {truck_id}: Saving original route before diversion")
                    update_data['originalRoute'] = truck.currentTrip
                
                logger.info(f"🚨 BEFORE UPDATE - Truck {truck_id} current status: {truck.status}")
                logger.info(f"🚨 UPDATE DATA: {update_data}")
                
                result_truck = truck_service.update_truck(truck_id, **update_data)
                
                logger.info(f"🚨 AFTER UPDATE - Truck {truck_id} new status: {result_truck.status if result_truck else 'UPDATE FAILED'}")
                logger.info(f"Truck {truck_id} updated with status: {update_data.get('status', 'N/A')}")
                
                # Note: Service pause and route restoration is now handled by the simulation engine
                # The simulation engine will detect when a DIVERTED truck reaches its service facility,
                # pause it for 1 minute, then restore the original route and change status back to ACTIVE
            
            # Resolve all active alerts for this truck
            truck_alerts = simulation_engine.get_truck_alerts(truck_id)
            resolved_count = 0
            
            logger.info(f"Found {len(truck_alerts)} alerts for truck {truck_id}")
            
            for alert in truck_alerts:
                logger.info(f"Processing alert {alert.alertId}: acknowledged={alert.acknowledged}")
                if not alert.acknowledged:
                    # Mark alert as acknowledged instead of deleting
                    alert.acknowledged = True
                    alert.acknowledgedAt = datetime.utcnow()
                    resolved_count += 1
                    logger.info(f"Acknowledged alert {alert.alertId} for truck {truck_id} at {alert.acknowledgedAt}")
            
            logger.info(f"Resolved {resolved_count} alerts for truck {truck_id}")
            
            # ALWAYS clear the truck's alertState and incidentType after decision is applied
            # This ensures the Fleet Status column shows the correct state
            # IMPORTANT: Preserve the status that was just set
            logger.info(f"Clearing alertState and incidentType for truck {truck_id} (before: incidentType={truck.incidentType}, alertState={truck.alertState})")
            
            result = truck_service.update_truck(truck_id, alertState=None, incidentType=None)
            
            if result:
                logger.info(f"Successfully cleared fields for truck {truck_id} (after: incidentType={result.incidentType}, alertState={result.alertState})")
            else:
                logger.error(f"Failed to update truck {truck_id} - truck not found")
            
            if resolved_count > 0:
                logger.info(f"Decision applied successfully: {resolved_count} alerts resolved for truck {truck_id}")
            else:
                logger.info(f"Decision applied successfully: No alerts to resolve for truck {truck_id}")
            
            logger.info(f"Decision applied successfully: {resolved_count} alerts resolved for truck {truck_id}")
            
        except Exception as e:
            logger.error(f"Error applying decision to truck {truck.truckId}: {e}", exc_info=True)
            # Don't raise - we don't want to fail the entire workflow if decision application fails


# Global instance
agent_service = AgentService()

# Made with Bob
