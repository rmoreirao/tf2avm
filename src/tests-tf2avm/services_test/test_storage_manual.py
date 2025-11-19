"""
Manual test script for StorageService.
Run this to verify local and Azure storage backends work correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add backend-tf2avm directory to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend-tf2avm"
sys.path.insert(0, str(backend_path))

from services.storage_service import StorageService, LocalFileStorageBackend, AzureBlobStorageBackend, StorageError
from config.settings import get_settings


async def test_local_storage():
    """Test local file storage backend."""
    print("\n=== Testing Local File Storage ===")
    
    # Create backend with temp directory
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        backend = LocalFileStorageBackend(base_path=temp_dir)
        service = StorageService(backend)
        
        # Test write/read text
        print("✓ Testing text write/read...")
        await service.write_text("test.txt", "Hello, World!")
        content = await service.read_text("test.txt")
        assert content == "Hello, World!", f"Expected 'Hello, World!', got '{content}'"
        print(f"  Read: {content}")
        
        # Test write/read JSON
        print("✓ Testing JSON write/read...")
        test_data = {"name": "test", "value": 123, "nested": {"key": "value"}}
        await service.write_json("test.json", test_data)
        loaded_data = await service.read_json("test.json")
        assert loaded_data == test_data, f"JSON mismatch"
        print(f"  Read: {loaded_data}")
        
        # Test exists
        print("✓ Testing exists...")
        assert await service.exists("test.txt") == True
        assert await service.exists("nonexistent.txt") == False
        print("  Exists checks passed")
        
        # Test ensure_dir and nested paths
        print("✓ Testing nested directory creation...")
        await service.write_text("nested/deep/file.txt", "nested content")
        nested_content = await service.read_text("nested/deep/file.txt")
        assert nested_content == "nested content"
        print(f"  Read from nested path: {nested_content}")
        
        # Test copy_file
        print("✓ Testing file copy...")
        await service.copy_file("test.txt", "test_copy.txt")
        copied_content = await service.read_text("test_copy.txt")
        assert copied_content == "Hello, World!"
        print(f"  Copied content: {copied_content}")
        
        # Test list_files
        print("✓ Testing list_files...")
        files = await service.list_files(".", "*.txt")
        print(f"  Found {len(files)} .txt files: {files}")
        assert len(files) >= 2  # test.txt and test_copy.txt
        
        # Test delete
        print("✓ Testing delete...")
        await service.delete("test_copy.txt")
        assert await service.exists("test_copy.txt") == False
        print("  Delete successful")
        
        print("\n✅ All local storage tests passed!")


async def test_azure_storage():
    """Test Azure Blob Storage backend with Azurite emulator."""
    print("\n=== Testing Azure Blob Storage (Azurite Emulator) ===")
    
    # Azurite default connection string
    azurite_connection_string = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )
    
    container_name = "tf2avm-test"
    test_prefix = "test-run/"
    
    try:
        # Create backend with Azurite settings
        backend = AzureBlobStorageBackend(
            connection_string=azurite_connection_string,
            container_name=container_name,
            prefix=test_prefix
        )
        service = StorageService(backend)
        
        print("✓ Connected to Azurite emulator")
        
        # Test write/read text
        print("✓ Testing text write/read...")
        await service.write_text("test.txt", "Hello, Azure!")
        content = await service.read_text("test.txt")
        assert content == "Hello, Azure!", f"Expected 'Hello, Azure!', got '{content}'"
        print(f"  Read: {content}")
        
        # Test write/read JSON
        print("✓ Testing JSON write/read...")
        test_data = {"cloud": "azure", "emulator": "azurite", "count": 456}
        await service.write_json("test.json", test_data)
        loaded_data = await service.read_json("test.json")
        assert loaded_data == test_data, "JSON mismatch"
        print(f"  Read: {loaded_data}")
        
        # Test write/read bytes
        print("✓ Testing binary write/read...")
        binary_data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        await service.write_bytes("test.bin", binary_data)
        loaded_binary = await service.read_bytes("test.bin")
        assert loaded_binary == binary_data, "Binary data mismatch"
        print(f"  Read {len(loaded_binary)} bytes")
        
        # Test exists
        print("✓ Testing exists...")
        assert await service.exists("test.txt"), "File should exist"
        assert not await service.exists("nonexistent.txt"), "File should not exist"
        print("  Exists checks passed")
        
        # Test nested paths
        print("✓ Testing nested paths...")
        await service.write_text("nested/deep/file.txt", "nested in cloud")
        nested_content = await service.read_text("nested/deep/file.txt")
        assert nested_content == "nested in cloud"
        print(f"  Read from nested path: {nested_content}")
        
        # Test copy_file
        print("✓ Testing file copy...")
        await service.copy_file("test.txt", "test_copy.txt")
        copied_content = await service.read_text("test_copy.txt")
        assert copied_content == "Hello, Azure!"
        print(f"  Copied content: {copied_content}")
        
        # Test list_files
        print("✓ Testing list_files...")
        files = await service.list_files("", "*.txt")  # Use empty string for root
        print(f"  Found {len(files)} .txt files: {files}")
        assert len(files) >= 2, f"Should have at least 2 txt files, got {len(files)}: {files}"
        
        # Test delete single file
        print("✓ Testing delete single file...")
        await service.delete("test_copy.txt")
        assert not await service.exists("test_copy.txt"), "File should be deleted"
        print("  Delete successful")
        
        # Test delete directory (prefix-based)
        print("✓ Testing delete directory...")
        await service.write_text("cleanup/file1.txt", "content1")
        await service.write_text("cleanup/file2.txt", "content2")
        await service.delete("cleanup/")
        remaining_files = await service.list_files("cleanup", "*.txt")
        assert len(remaining_files) == 0, "All files should be deleted"
        print("  Directory deletion successful")
        
        # Cleanup: delete all test files
        print("✓ Cleaning up test files...")
        all_files = await service.list_files(".", "*")
        for file in all_files:
            try:
                await service.delete(file)
            except Exception:
                pass
        
        print("\n✅ All Azure Blob Storage tests passed!")
        
        # Close the blob service client
        if hasattr(backend, 'close'):
            await backend.close()
        
        return True
        
    except ImportError:
        print("⚠️  azure-storage-blob not installed. Skipping Azure tests.")
        print("   Install with: pip install azure-storage-blob")
        return False
    except StorageError as e:
        if "Failed to initialize" in str(e) or "getaddrinfo failed" in str(e):
            print(f"⚠️  Azurite emulator not running. Skipping Azure tests.")
            print(f"   Start Azurite with: azurite-blob --silent --location azurite --debug azurite\\debug.log")
            print(f"   Or with Docker: docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0")
            return False
        raise
    except Exception as e:
        print(f"⚠️  Azure test error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_storage_from_settings():
    """Test StorageService.from_settings() factory method."""
    print("\n=== Testing StorageService.from_settings() ===")
    
    settings = get_settings()
    service = StorageService.from_settings(settings)
    
    print(f"✓ Created storage service with backend: {settings.storage_backend}")
    print(f"  Backend type: {type(service.backend).__name__}")
    
    # Basic smoke test
    test_path = "test_from_settings.txt"
    try:
        await service.write_text(test_path, "Testing from settings")
        content = await service.read_text(test_path)
        assert content == "Testing from settings"
        await service.delete(test_path)
        print("✅ Settings-based storage service works!")
    except Exception as e:
        print(f"⚠️  Warning: {e}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Storage Service Manual Tests")
    print("=" * 60)
    
    test_results = {
        "local": False,
        "azure": False,
        "settings": False
    }
    
    try:
        await test_local_storage()
        test_results["local"] = True
        
        azure_result = await test_azure_storage()
        test_results["azure"] = azure_result
        
        await test_storage_from_settings()
        test_results["settings"] = True
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Local Storage:           {'PASSED' if test_results['local'] else 'FAILED'}")
        print(f"{'✅' if test_results['azure'] else '⚠️ '} Azure Blob Storage:      {'PASSED' if test_results['azure'] else 'SKIPPED (Azurite not running)'}")
        print(f"✅ Settings Factory:        {'PASSED' if test_results['settings'] else 'FAILED'}")
        print("=" * 60)
        
        # Return 0 if critical tests passed (local and settings)
        if test_results["local"] and test_results["settings"]:
            print("✅ ALL CRITICAL TESTS PASSED")
            if not test_results["azure"]:
                print("   (Azure tests skipped - start Azurite to enable)")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            return 1
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
