FROM docker.io/node:18-alpine

RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 && \
    mkdir -p /app && \
    chown nodejs:nodejs /app

WORKDIR /app

USER nodejs

COPY --chown=nodejs:nodejs package*.json ./

RUN npm install --production

COPY --chown=nodejs:nodejs . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:8080/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

CMD ["node", "server.js"]