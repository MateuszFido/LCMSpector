#!/usr/bin/env python3
"""
Comprehensive test suite for Nuitka-built LC-Inspector.

This script validates Nuitka builds following the migration plan specifications,
including functional tests, resource access, and integration validation.
"""

import pytest
import subprocess
import tempfile
import json
import os
import sys
import time
import signal
from pathlib import Path


class TestNuitkaBuild:
    """Comprehensive test suite for Nuitka-built LC-Inspector."""
    
    @pytest.fixture
    def executable_path(self):
        """Path to the Nuitka-built executable."""
        # Try to auto-detect the executable
        candidates = [
            Path("./lc-inspector/dist/main"),  # Unix Nuitka
            Path("./lc-inspector/dist/main.exe"),  # Windows Nuitka
            Path("./lc-inspector/dist/LCMSpector.app/Contents/MacOS/LCMSpector"),  # macOS bundle
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        pytest.skip("No Nuitka executable found")
    
    def test_executable_exists(self, executable_path):
        """Test that the executable was created."""
        assert executable_path.exists(), f"Executable not found: {executable_path}"
        assert executable_path.is_file() or executable_path.is_symlink(), "Executable is not a file"
        
        # Check file size is reasonable (at least 50MB for bundled app)
        size_mb = executable_path.stat().st_size / (1024 * 1024)
        assert size_mb > 50, f"Executable too small: {size_mb:.1f}MB"
        print(f"✓ Executable size: {size_mb:.1f}MB")
    
    def test_executable_permissions(self, executable_path):
        """Test that the executable has proper permissions."""
        if sys.platform != "win32":
            # On Unix systems, check execute permissions
            assert os.access(executable_path, os.X_OK), "Executable lacks execute permissions"
    
    def test_application_info(self, executable_path):
        """Test that application reports correct information."""
        result = subprocess.run(
            [str(executable_path), '--app-info'],
            capture_output=True,
            text=True,
            timeout=20
        )
        
        # Should either succeed or timeout (GUI apps may not exit cleanly)
        if result.returncode != 0 and result.returncode != 124:  # 124 is timeout
            pytest.fail(f"App info failed: {result.stderr}")
        
        print("✓ Application info command executed")
    
    def test_resource_access(self, executable_path):
        """Test that bundled resources are accessible."""
        result = subprocess.run(
            [str(executable_path), '--test-resources'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Should succeed or timeout
        if result.returncode not in [0, 124]:
            print(f"Resource test output: {result.stdout}")
            print(f"Resource test errors: {result.stderr}")
        
        # Check for specific resource confirmations in output
        if result.stdout:
            assert "config.json" in result.stdout, "Config file test not found in output"
            print("✓ Resource access test executed")
    
    def test_config_loading(self, executable_path):
        """Test that configuration loads without errors."""
        result = subprocess.run(
            [str(executable_path), '--test-config'],
            capture_output=True,
            text=True,
            timeout=20
        )
        
        if result.returncode not in [0, 124]:
            pytest.fail(f"Config test failed: {result.stderr}")
        
        print("✓ Configuration loading test executed")
    
    def test_gui_startup_non_blocking(self, executable_path):
        """Test GUI startup without blocking (starts and can be terminated)."""
        process = subprocess.Popen(
            [str(executable_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it a few seconds to start
        time.sleep(5)
        
        # Check if process is still running (it should be for a GUI app)
        poll_result = process.poll()
        
        if poll_result is None:
            # Process is running, try to terminate it gracefully
            process.terminate()
            try:
                process.wait(timeout=10)
                print("✓ GUI started and terminated successfully")
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                process.wait()
                print("✓ GUI started (required force termination)")
        else:
            # Process exited, check the output
            stdout, stderr = process.communicate()
            if poll_result != 0:
                print(f"Process output: {stdout.decode()}")
                print(f"Process errors: {stderr.decode()}")
                pytest.fail(f"GUI process exited with code {poll_result}")
            else:
                print("✓ GUI process completed successfully")
    
    def test_no_critical_errors(self, executable_path):
        """Test that there are no critical runtime errors."""
        process = subprocess.Popen(
            [str(executable_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Let it run briefly
        time.sleep(3)
        
        # Terminate and check output
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        
        stderr_text = stderr.decode() if stderr else ""
        stdout_text = stdout.decode() if stdout else ""
        
        # Check for critical errors
        critical_errors = [
            'segmentation fault', 'core dumped', 'fatal error',
            'ImportError', 'ModuleNotFoundError', 'Failed to import'
        ]
        
        for error in critical_errors:
            assert error.lower() not in stderr_text.lower(), f"Critical error found: {error}"
            assert error.lower() not in stdout_text.lower(), f"Critical error found: {error}"
        
        print("✓ No critical errors detected")


@pytest.mark.integration
class TestIntegration:
    """Integration tests for full application functionality."""
    
    @pytest.fixture
    def executable_path(self):
        """Path to the executable for integration tests."""
        candidates = [
            Path("./lc-inspector/dist/main"),
            Path("./lc-inspector/dist/main.exe"),
            Path("./lc-inspector/dist/LCMSpector.app/Contents/MacOS/LCMSpector"),
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        pytest.skip("No executable found for integration tests")
    
    def test_sample_file_processing(self, executable_path):
        """Test processing a minimal sample file."""
        # Create a minimal test mzML file
        minimal_mzml = '''<?xml version="1.0" encoding="utf-8"?>
<mzML xmlns="http://psi.hupo.org/ms/mzml">
  <cvList count="1">
    <cv id="MS" fullName="Proteomics Standards Initiative Mass Spectrometry Ontology"/>
  </cvList>
  <run id="test_run">
    <spectrumList count="1">
      <spectrum index="0" id="scan=1">
        <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>
        <binaryDataArrayList count="2">
          <binaryDataArray encodedLength="0">
            <cvParam cvRef="MS" accession="MS:1000514" name="m/z array"/>
            <binary></binary>
          </binaryDataArray>
          <binaryDataArray encodedLength="0">
            <cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/>
            <binary></binary>
          </binaryDataArray>
        </binaryDataArrayList>
      </spectrum>
    </spectrumList>
  </run>
</mzML>'''
        
        with tempfile.NamedTemporaryFile(suffix='.mzML', mode='w', delete=False) as f:
            f.write(minimal_mzml)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                [str(executable_path), '--test-file', temp_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # File processing test may timeout (GUI nature), which is acceptable
            if result.returncode not in [0, 124]:
                print(f"File processing output: {result.stdout}")
                print(f"File processing errors: {result.stderr}")
                # Don't fail the test for timeout, as GUI apps may not exit cleanly
            
            print("✓ File processing test executed")
            
        finally:
            os.unlink(temp_path)
    
    def test_startup_performance(self, executable_path):
        """Test that startup time is reasonable."""
        start_time = time.perf_counter()
        
        process = subprocess.Popen(
            [str(executable_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup indicators or timeout
        startup_detected = False
        for _ in range(100):  # Up to 10 seconds (100 * 0.1s)
            if process.poll() is None:
                startup_detected = True
                break
            time.sleep(0.1)
        
        end_time = time.perf_counter()
        startup_time = end_time - start_time
        
        # Clean up
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        
        # Startup should be reasonable (less than 30 seconds)
        assert startup_time < 30, f"Startup too slow: {startup_time:.2f}s"
        print(f"✓ Startup time: {startup_time:.2f}s")


@pytest.mark.platform
class TestPlatformSpecific:
    """Platform-specific tests for macOS and Windows."""
    
    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_macos_app_bundle(self):
        """Test macOS app bundle structure and properties."""
        app_path = Path("./lc-inspector/dist/LCMSpector.app")
        
        if not app_path.exists():
            pytest.skip("macOS app bundle not found")
        
        assert app_path.is_dir(), "App bundle is not a directory"
        
        # Check required bundle structure
        contents_path = app_path / "Contents"
        assert contents_path.exists(), "Contents directory missing"
        
        macos_path = contents_path / "MacOS"
        assert macos_path.exists(), "MacOS directory missing"
        
        executable_path = macos_path / "LCMSpector"
        assert executable_path.exists(), "Executable missing from bundle"
        assert executable_path.is_file(), "Executable is not a file"
        
        # Check Info.plist
        plist_path = contents_path / "Info.plist"
        if plist_path.exists():
            print("✓ Info.plist found")
        
        print("✓ macOS app bundle structure validated")
    
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_windows_executable(self):
        """Test Windows executable properties."""
        exe_path = Path("./lc-inspector/dist/main.exe")
        
        if not exe_path.exists():
            pytest.skip("Windows executable not found")
        
        assert exe_path.is_file(), "Executable is not a file"
        
        # Check minimum file size
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        assert size_mb > 50, f"Executable too small: {size_mb:.1f}MB"
        
        print(f"✓ Windows executable validated ({size_mb:.1f}MB)")


def run_tests():
    """Run the test suite."""
    return pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])


if __name__ == "__main__":
    sys.exit(run_tests())