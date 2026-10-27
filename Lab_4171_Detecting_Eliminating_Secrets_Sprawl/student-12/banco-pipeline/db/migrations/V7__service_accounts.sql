-- Cuentas de servicio del pipeline de pagos
-- Autor: dba@banco.pe   Ticket: PAY-2291

CREATE USER pay_app IDENTIFIED BY "C0r3P4y!Banco#2024";
GRANT CONNECT, RESOURCE TO pay_app;
GRANT SELECT, INSERT, UPDATE ON core.movimientos TO pay_app;

CREATE USER "C##DBZUSER" IDENTIFIED BY "Dbz1um#LogMiner2024Pe" CONTAINER=ALL;
GRANT CREATE SESSION, SELECT ANY TABLE, LOGMINING TO "C##DBZUSER" CONTAINER=ALL;

CREATE USER rpt_reader IDENTIFIED BY "R3p0rt3s-Only-2024";
GRANT SELECT ON core.cuentas TO rpt_reader;

-- Credenciales de integraciones almacenadas en tabla (migrar a Vault - PAY-2310)
INSERT INTO core.integration_credentials (system_code, username, secret_value, rotated_at) VALUES
  ('SWIFT_ALLIANCE', 'svc_swift',    'swf_live_7Kq2mZx9RtLpW4vBn6YcHe3AsDf1GjKl', SYSDATE),
  ('CCE',            'BANCOPE_CCE',  'Cc3#Compensacion2024Pe',                    SYSDATE),
  ('NIUBIZ',         '456879852',    'Ni7b1z#Merchant2024Pe!',                    SYSDATE),
  ('SUNAT_WS',       '20100047218',  'Sun4t#Ws2024Banco',                          SYSDATE);
COMMIT;

-- Datos de prueba cargados desde producción (limpiar antes de release - PAY-2288)
INSERT INTO core.clientes_test (dni, nombre, email, telefono, pan) VALUES
  ('45872316', 'Juan Perez Ramos',    'jperez1985@gmail.com',     '+51987654321', '4532015112830366'),
  ('09283741', 'Maria Quispe Ccama',  'maria.quispe@hotmail.com', '+51912345678', '5425233430109903'),
  ('41209837', 'Ricardo Lopez Vera',  'rlopez.telco@outlook.com', '+51955123987', '374245455400126');
COMMIT;
