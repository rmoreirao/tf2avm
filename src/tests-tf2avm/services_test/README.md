# Storage Service Tests

This directory contains tests for the unified storage service supporting both local filesystem and Azure Blob Storage backends.

## Test Files

- `test_storage_manual.py` - Comprehensive manual tests for all storage backends

## Running Tests

### Prerequisites

```bash
# Install required packages
pip install azure-storage-blob
```

### Local Storage Tests Only

```bash
python test_storage_manual.py
```

This will run local filesystem tests and skip Azure tests if Azurite is not running.

### Full Tests (Including Azure Blob Storage)

To test Azure Blob Storage functionality, you need to run **Azurite** (Azure Storage Emulator).

#### Option 1: Install Azurite Locally

```bash
# Install Azurite globally
npm install -g azurite

# Start Azurite blob service
azurite-blob --silent --location azurite --debug azurite\debug.log
```

Then run tests:
```bash
python test_storage_manual.py
```

#### Option 2: Run Azurite with Docker

```bash
# Start Azurite container
docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 `
  mcr.microsoft.com/azure-storage/azurite `
  azurite-blob --blobHost 0.0.0.0

# In another terminal, run tests
python test_storage_manual.py
```

#### Option 3: Use Docker Compose (Recommended)

Create `docker-compose.yml` in your project root:

```yaml
version: '3.8'
services:
  azurite:
    image: mcr.microsoft.com/azure-storage/azurite
    container_name: azurite
    ports:
      - "10000:10000"  # Blob service
      - "10001:10001"  # Queue service
      - "10002:10002"  # Table service
    volumes:
      - azurite-data:/data
    command: azurite-blob --blobHost 0.0.0.0 --blobPort 10000

volumes:
  azurite-data:
```

Start Azurite:
```bash
docker-compose up -d azurite
```

Run tests:
```bash
python test_storage_manual.py
```

Stop Azurite:
```bash
docker-compose down
```

## Test Coverage

### Local File Storage Backend
- ✅ Text file read/write (UTF-8)
- ✅ Binary file read/write
- ✅ JSON serialization/deserialization
- ✅ File existence checks
- ✅ Nested directory creation
- ✅ File copying
- ✅ File listing with glob patterns
- ✅ File/directory deletion

### Azure Blob Storage Backend
- ✅ Text blob read/write (UTF-8)
- ✅ Binary blob read/write
- ✅ JSON blob serialization/deserialization
- ✅ Blob existence checks
- ✅ Virtual directory handling
- ✅ Blob copying
- ✅ Blob listing with prefix filtering
- ✅ Single blob deletion
- ✅ Prefix-based deletion (directory-like)
- ✅ Proper content-type headers

### Settings-Based Factory
- ✅ StorageService.from_settings() instantiation
- ✅ Backend selection from configuration
- ✅ Integration with application settings

## Expected Output

### All Tests Passing (with Azurite)

```
============================================================
Storage Service Manual Tests
============================================================

=== Testing Local File Storage ===
✓ Testing text write/read...
  Read: Hello, World!
✓ Testing JSON write/read...
  Read: {'name': 'test', 'value': 123, 'nested': {'key': 'value'}}
✓ Testing exists...
  Exists checks passed
✓ Testing nested directory creation...
  Read from nested path: nested content
✓ Testing file copy...
  Copied content: Hello, World!
✓ Testing list_files...
  Found 2 .txt files: ['test.txt', 'test_copy.txt']
✓ Testing delete...
  Delete successful

✅ All local storage tests passed!

=== Testing Azure Blob Storage (Azurite Emulator) ===
✓ Connected to Azurite emulator
✓ Testing text write/read...
  Read: Hello, Azure!
✓ Testing JSON write/read...
  Read: {'cloud': 'azure', 'emulator': 'azurite', 'count': 456}
✓ Testing binary write/read...
  Read 7 bytes
✓ Testing exists...
  Exists checks passed
✓ Testing nested paths...
  Read from nested path: nested in cloud
✓ Testing file copy...
  Copied content: Hello, Azure!
✓ Testing list_files...
  Found 3 .txt files
✓ Testing delete single file...
  Delete successful
✓ Testing delete directory...
  Directory deletion successful
✓ Cleaning up test files...

✅ All Azure Blob Storage tests passed!

=== Testing StorageService.from_settings() ===
✓ Created storage service with backend: local
  Backend type: LocalFileStorageBackend
✅ Settings-based storage service works!

============================================================
TEST SUMMARY
============================================================
✅ Local Storage:           PASSED
✅ Azure Blob Storage:      PASSED
✅ Settings Factory:        PASSED
============================================================
✅ ALL CRITICAL TESTS PASSED
```

### Without Azurite (Azure Tests Skipped)

```
============================================================
Storage Service Manual Tests
============================================================

=== Testing Local File Storage ===
[... local tests ...]
✅ All local storage tests passed!

=== Testing Azure Blob Storage (Azurite Emulator) ===
⚠️  Azurite emulator not running. Skipping Azure tests.
   Start Azurite with: azurite-blob --silent --location azurite --debug azurite\debug.log
   Or with Docker: docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0

=== Testing StorageService.from_settings() ===
[... settings tests ...]
✅ Settings-based storage service works!

============================================================
TEST SUMMARY
============================================================
✅ Local Storage:           PASSED
⚠️  Azure Blob Storage:      SKIPPED (Azurite not running)
✅ Settings Factory:        PASSED
============================================================
✅ ALL CRITICAL TESTS PASSED
   (Azure tests skipped - start Azurite to enable)
```

## Troubleshooting

### Azurite Connection Issues

If you see connection errors:
1. Ensure Azurite is running: `docker ps` or check if the process is running
2. Check port 10000 is not in use: `netstat -an | findstr 10000`
3. Verify firewall settings allow local connections

### Module Import Errors

If you see import errors:
```bash
# Ensure you're in the virtual environment
D:/repos/tf2avm/.venv/Scripts/python.exe test_storage_manual.py
```

### Azure Storage Package Missing

```bash
pip install azure-storage-blob>=12.19.0
```

## Integration with CI/CD

For CI/CD pipelines, use Docker Compose to ensure Azurite is available:

```yaml
# .github/workflows/test.yml or similar
services:
  azurite:
    image: mcr.microsoft.com/azure-storage/azurite
    ports:
      - 10000:10000
      - 10001:10001
      - 10002:10002
```

## Azurite Configuration

Default Azurite connection string (used in tests):
```
DefaultEndpointsProtocol=http;
AccountName=devstoreaccount1;
AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;
BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;
```

This is a well-known development credential for local testing only. **Never use in production!**
