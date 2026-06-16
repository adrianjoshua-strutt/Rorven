# Backup and restore requirements

Before stable release, document and test:

- PostgreSQL backup and point-in-time recovery expectations
- secret-store backup without exporting raw values into project artifacts
- artifact-store backup
- restoration into a clean deployment
- reconciliation of in-flight leases and scheduled jobs after restore
- recovery verification checklist
