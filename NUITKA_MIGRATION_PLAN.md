# LC-Inspector Nuitka Migration Implementation Plan

## Executive Summary

This document outlines a **direct migration from PyInstaller to Nuitka** for LC-Inspector, targeting **40-70% startup performance improvements** while maintaining full functionality across macOS and Windows platforms.

## Current Architecture Analysis

### Application Stack
- **Framework**: PyQt6 6.9.1 with pyqtgraph 0.13.7
- **Scientific Libraries**: NumPy 2.3.1, Pandas 2.3.1, SciPy 1.16.0, pyteomics 4.7.2
- **Platform Support**: macOS (arm64), Windows (x86_64)
- **Python Version**: 3.12

### Current PyInstaller Configuration Analysis
- **Spec File**: [`LCMSpector.spec`](lc-inspector/LCMSpector.spec:1) with sophisticated platform-specific handling
- **Resources**: Large MS library (~100MB MoNA-export), config files, UI assets
- **Excludes**: Heavy modules (torch, matplotlib, frozendict) for size optimization
- **macOS**: App bundle with Info.plist privacy keys for Qt CoreLocation
- **Windows**: One-folder distribution with proper file structure

### Key Migration Challenges Identified
1. **PyQt6 Integration**: Complex Qt plugin system and platform-specific requirements
2. **Scientific Stack**: Large numpy/scipy dependencies with optimized binaries
3. **Resource Bundling**: ~100MB MS library file needs efficient inclusion
4. **Cross-Platform Builds**: Different packaging requirements for macOS vs Windows
5. **CI/CD Integration**: GitHub Actions workflows need Nuitka-specific modifications

---

## Migration Strategy: Direct Nuitka Implementation

**Timeline**: 3-4 weeks
**Goal**: 40-70% startup performance improvement with full feature parity

---

## Technical Implementation Details

### 1. Core Nuitka Configuration

#### Base Configuration Template
```bash
python -m nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyqt6 \
    --enable-plugin=numpy \
    --python-flag=no_site \
    --python-flag=-O \
    --include-data-dir=lc-inspector/resources=resources \
    --include-data-file=lc-inspector/config.json=config.json \
    --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm \
    lc-inspector/main.py
```

### 2. Platform-Specific Configurations

#### macOS Configuration
```bash
# nuitka_build_macos.sh
#!/bin/bash
python -m nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyqt6 \
    --enable-plugin=numpy \
    --macos-create-app-bundle \
    --macos-app-icon=lc-inspector/icon.icns \
    --macos-app-name="LCMSpector" \
    --macos-app-version="1.0.0" \
    --macos-signed-app-name="com.ethz.lcmspector" \
    --include-data-dir=lc-inspector/resources=resources \
    --include-data-file=lc-inspector/config.json=config.json \
    --include-data-file=lc-inspector/ui/logo.png=ui/logo.png \
    --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm \
    --python-flag=no_site \
    --python-flag=-O \
    --output-dir=dist \
    lc-inspector/main.py
```

#### Windows Configuration
```batch
REM nuitka_build_windows.bat
python -m nuitka ^
    --standalone ^
    --onefile ^
    --enable-plugin=pyqt6 ^
    --enable-plugin=numpy ^
    --windows-icon-from-ico=lc-inspector/icon.icns ^
    --windows-company-name="ETH Zurich" ^
    --windows-product-name="LCMSpector" ^
    --windows-file-version="1.0.0" ^
    --windows-product-version="1.0.0" ^
    --include-data-dir=lc-inspector/resources=resources ^
    --include-data-file=lc-inspector/config.json=config.json ^
    --include-data-file=lc-inspector/ui/logo.png=ui/logo.png ^
    --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm ^
    --python-flag=no_site ^
    --python-flag=-O ^
    --output-dir=dist ^
    lc-inspector/main.py
```

### 3. Resource Bundling Strategy

#### Resource Path Resolution for Nuitka
```python
# utils/resources.py - New utility for Nuitka compatibility
import os
import sys
from pathlib import Path

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for development and Nuitka builds.
    
    Nuitka uses different resource location strategies than PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        # Nuitka standalone build
        if hasattr(sys, '_MEIPASS'):
            # Fallback for PyInstaller compatibility during transition
            base_path = sys._MEIPASS
        else:
            # Nuitka standard resource location
            base_path = Path(sys.executable).parent
        return os.path.join(base_path, relative_path)
    else:
        # Development environment
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', relative_path)

def load_config():
    """Load configuration with Nuitka-compatible path resolution."""
    config_path = get_resource_path('config.json')
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    import json
    with open(config_path, 'r') as f:
        return json.load(f)

def get_msp_library_path():
    """Get path to MS library file."""
    return get_resource_path('resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp')
```

#### Update Main Application for Nuitka
```python
# main.py modifications for Nuitka compatibility
import os
import sys
from utils.resources import get_resource_path, load_config  # New import

# Update icon loading
def load_application_icon(app):
    """Load application icon with Nuitka-compatible path."""
    icon_path = get_resource_path('resources/icon.icns')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Warning: Icon not found at {icon_path}")

# Update configuration loading in main()
def main():
    """Main entry point with Nuitka compatibility."""
    logger = configure_logging()
    logger.info("Starting LCMSpector with Nuitka build...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("LCMSpector")
    app.setApplicationVersion("1.0.0")
    
    # Load icon with new resource system
    load_application_icon(app)
    
    # Create model, view, and controller with updated config loading
    try:
        config = load_config()  # Use new config loader
        model = Model(config)
        view = View()
        controller = Controller(model, view)
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        sys.exit(1)
    
    app.setStyle("Fusion")
    view.show()
    
    logger.info("Application initialized successfully")
    sys.exit(app.exec())
```

### 4. Large File Handling Strategy

#### Option A: Include in Binary (Recommended for simplicity)
```bash
# Include the large MSP file directly in the binary
--include-data-file=lc-inspector/resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp=resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp
```

#### Option B: External File Distribution (For very large files)
```python
# external_resources.py - For handling external large files
import os
import urllib.request
from pathlib import Path

class ExternalResourceManager:
    """Manage external resources that are too large for binary inclusion."""
    
    def __init__(self):
        self.resources_dir = Path.home() / '.lcmspector' / 'resources'
        self.resources_dir.mkdir(parents=True, exist_ok=True)
    
    def ensure_msp_library(self):
        """Ensure MSP library is available, download if needed."""
        msp_path = self.resources_dir / 'MoNA-export-All_LC-MS-MS_Orbitrap.msp'
        
        if not msp_path.exists():
            print("Downloading MS library...")
            url = "https://polybox.ethz.ch/index.php/s/CrnWdgwX5canNxL/download"
            urllib.request.urlretrieve(url, str(msp_path))
        
        return str(msp_path)
```

---

## Performance Benchmarking Methodology

### 1. Startup Time Measurement
```python
# benchmark_startup.py
import time
import subprocess
import statistics
import json
from pathlib import Path

class StartupBenchmark:
    """Benchmark application startup performance."""
    
    def __init__(self):
        self.results = {}
    
    def measure_startup(self, executable_path, iterations=10):
        """Measure startup time with statistical analysis."""
        times = []
        
        for i in range(iterations):
            # Use a special flag to exit immediately after initialization
            start_time = time.perf_counter()
            
            result = subprocess.run(
                [str(executable_path), '--benchmark-startup'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            end_time = time.perf_counter()
            
            if result.returncode == 0:
                startup_time = end_time - start_time
                times.append(startup_time)
                print(f"Run {i+1:2d}: {startup_time:6.3f}s")
            else:
                print(f"Run {i+1:2d}: FAILED - {result.stderr}")
        
        if times:
            return {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                'min': min(times),
                'max': max(times),
                'count': len(times)
            }
        return None
    
    def compare_builds(self, pyinstaller_exe, nuitka_exe):
        """Compare PyInstaller vs Nuitka performance."""
        print("Benchmarking PyInstaller build...")
        pyinstaller_stats = self.measure_startup(pyinstaller_exe)
        
        print("\nBenchmarking Nuitka build...")
        nuitka_stats = self.measure_startup(nuitka_exe)
        
        if pyinstaller_stats and nuitka_stats:
            improvement = ((pyinstaller_stats['mean'] - nuitka_stats['mean']) 
                          / pyinstaller_stats['mean'] * 100)
            
            print(f"\n{'='*50}")
            print(f"PERFORMANCE COMPARISON")
            print(f"{'='*50}")
            print(f"PyInstaller: {pyinstaller_stats['mean']:.3f}s ± {pyinstaller_stats['stdev']:.3f}s")
            print(f"Nuitka:      {nuitka_stats['mean']:.3f}s ± {nuitka_stats['stdev']:.3f}s")
            print(f"Improvement: {improvement:+.1f}%")
            
            return {
                'pyinstaller': pyinstaller_stats,
                'nuitka': nuitka_stats,
                'improvement_percent': improvement
            }
        
        return None

# Usage
if __name__ == "__main__":
    benchmark = StartupBenchmark()
    results = benchmark.compare_builds(
        './dist_pyinstaller/LCMSpector',
        './dist_nuitka/LCMSpector'
    )
```

### 2. Memory Usage Analysis
```python
# benchmark_memory.py
import psutil
import time
import subprocess
import threading
from collections import defaultdict

class MemoryBenchmark:
    """Monitor memory usage during application lifecycle."""
    
    def __init__(self):
        self.samples = []
        self.monitoring = False
    
    def monitor_process(self, pid, duration=60):
        """Monitor memory usage of a process."""
        try:
            process = psutil.Process(pid)
            start_time = time.time()
            
            while self.monitoring and (time.time() - start_time) < duration:
                try:
                    memory_info = process.memory_info()
                    cpu_percent = process.cpu_percent()
                    
                    self.samples.append({
                        'timestamp': time.time() - start_time,
                        'rss_mb': memory_info.rss / 1024 / 1024,
                        'vms_mb': memory_info.vms / 1024 / 1024,
                        'cpu_percent': cpu_percent
                    })
                    
                    time.sleep(0.5)  # Sample every 500ms
                    
                except psutil.NoSuchProcess:
                    break
                    
        except psutil.NoSuchProcess:
            pass
    
    def benchmark_memory_usage(self, executable_path):
        """Benchmark memory usage during typical operation."""
        self.samples = []
        self.monitoring = True
        
        # Start the application
        process = subprocess.Popen([str(executable_path)])
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(
            target=self.monitor_process,
            args=(process.pid, 60)
        )
        monitor_thread.start()
        
        # Wait for monitoring to complete
        monitor_thread.join()
        self.monitoring = False
        
        # Terminate the application
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        
        return self.analyze_samples()
    
    def analyze_samples(self):
        """Analyze memory usage samples."""
        if not self.samples:
            return None
        
        rss_values = [s['rss_mb'] for s in self.samples]
        cpu_values = [s['cpu_percent'] for s in self.samples]
        
        return {
            'peak_memory_mb': max(rss_values),
            'avg_memory_mb': sum(rss_values) / len(rss_values),
            'startup_memory_mb': rss_values[0] if rss_values else 0,
            'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
            'sample_count': len(self.samples)
        }
```

---

## Testing and Validation Framework

### 1. Automated Build Validation
```python
# test_nuitka_build.py
import pytest
import subprocess
import tempfile
import json
import os
from pathlib import Path

class TestNuitkaBuild:
    """Comprehensive test suite for Nuitka-built LC-Inspector."""
    
    @pytest.fixture
    def executable_path(self):
        """Path to the Nuitka-built executable."""
        return Path("./dist/main")  # Adjust based on actual output
    
    def test_executable_exists(self, executable_path):
        """Test that the executable was created."""
        assert executable_path.exists(), f"Executable not found: {executable_path}"
        assert executable_path.is_file(), "Executable is not a file"
        
        # Check file size is reasonable (at least 50MB for bundled app)
        size_mb = executable_path.stat().st_size / (1024 * 1024)
        assert size_mb > 50, f"Executable too small: {size_mb:.1f}MB"
    
    def test_application_version(self, executable_path):
        """Test that application reports correct version."""
        result = subprocess.run(
            [str(executable_path), '--version'],
            capture_output=True,
            text=True,
            timeout=15
        )
        assert result.returncode == 0, f"Version check failed: {result.stderr}"
        assert "LCMSpector" in result.stdout, "Application name not in version output"
    
    def test_config_loading(self, executable_path):
        """Test that configuration loads without errors."""
        result = subprocess.run(
            [str(executable_path), '--test-config'],
            capture_output=True,
            text=True,
            timeout=20
        )
        assert result.returncode == 0, f"Config test failed: {result.stderr}"
    
    def test_gui_startup(self, executable_path):
        """Test GUI startup without crashes."""
        # Start application and immediately close
        process = subprocess.Popen(
            [str(executable_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it a few seconds to start
        try:
            stdout, stderr = process.communicate(timeout=10)
            # Process should still be running at this point
            # We'll terminate it manually
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # This is expected - GUI should keep running
            process.terminate()
            process.wait(timeout=5)
        
        # Check for critical errors in stderr
        stderr_text = stderr.decode() if stderr else ""
        critical_errors = ['segmentation fault', 'core dumped', 'fatal error']
        for error in critical_errors:
            assert error.lower() not in stderr_text.lower(), f"Critical error: {error}"
    
    def test_resource_access(self, executable_path):
        """Test that bundled resources are accessible."""
        result = subprocess.run(
            [str(executable_path), '--test-resources'],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Resource test failed: {result.stderr}"
        assert "config.json: OK" in result.stdout, "Config file not accessible"
        assert "logo.png: OK" in result.stdout, "Logo file not accessible"

@pytest.mark.integration
class TestIntegration:
    """Integration tests for full application functionality."""
    
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
                timeout=45
            )
            assert result.returncode == 0, f"File processing failed: {result.stderr}"
        finally:
            os.unlink(temp_path)

# Run with: pytest test_nuitka_build.py -v
```

### 2. Cross-Platform Validation
```python
# test_platform_specific.py
import platform
import pytest
import subprocess
from pathlib import Path

class TestPlatformSpecific:
    """Platform-specific tests for macOS and Windows."""
    
    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS only")
    def test_macos_app_bundle(self):
        """Test macOS app bundle structure and properties."""
        app_path = Path("./dist/LCMSpector.app")
        assert app_path.exists(), "App bundle not found"
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
        assert plist_path.exists(), "Info.plist missing"
        
        # Test bundle execution
        result = subprocess.run(
            ['open', '-a', str(app_path), '--args', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Note: open command behavior may vary
        
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
    def test_windows_executable(self):
        """Test Windows executable properties."""
        exe_path = Path("./dist/main.exe")
        assert exe_path.exists(), "Windows executable not found"
        assert exe_path.is_file(), "Executable is not a file"
        
        # Check minimum file size
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        assert size_mb > 50, f"Executable too small: {size_mb:.1f}MB"
        
        # Test execution
        result = subprocess.run(
            [str(exe_path), '--version'],
            capture_output=True,
            text=True,
            timeout=15
        )
        assert result.returncode == 0, f"Execution failed: {result.stderr}"
    
    def test_startup_time_platform_appropriate(self):
        """Test that startup time is appropriate for the platform."""
        import time
        
        if platform.system() == "Darwin":
            executable = Path("./dist/LCMSpector.app/Contents/MacOS/LCMSpector")
        elif platform.system() == "Windows":
            executable = Path("./dist/main.exe")
        else:
            pytest.skip("Unsupported platform")
        
        # Measure startup time
        start_time = time.perf_counter()
        result = subprocess.run(
            [str(executable), '--benchmark-startup'],
            capture_output=True,
            timeout=30
        )
        end_time = time.perf_counter()
        
        startup_time = end_time - start_time
        
        # Platform-specific expectations
        if platform.system() == "Darwin":
            max_startup_time = 5.0  # macOS app bundles can be slower
        else:
            max_startup_time = 3.0  # Windows should be faster
        
        assert startup_time < max_startup_time, f"Startup too slow: {startup_time:.2f}s"
        assert result.returncode == 0, "Startup failed"
```

---

## Fallback Strategy

### 1. Automated Fallback System
```python
# fallback_manager.py
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

class NuitkaMigrationManager:
    """Manage Nuitka migration with automated fallback to PyInstaller."""
    
    def __init__(self, project_root=Path('.')):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / 'dist_backup'
        self.nuitka_dir = self.project_root / 'dist_nuitka'
        self.current_dir = self.project_root / 'dist'
        self.validation_results = {}
    
    def backup_current_build(self):
        """Create backup of current PyInstaller build."""
        if self.current_dir.exists():
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            
            shutil.copytree(self.current_dir, self.backup_dir)
            
            # Save metadata
            metadata = {
                'backup_date': datetime.now().isoformat(),
                'original_build_system': 'pyinstaller',
                'backup_size_mb': sum(f.stat().st_size for f in self.backup_dir.rglob('*') if f.is_file()) / (1024*1024)
            }
            
            with open(self.backup_dir / 'backup_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
        return False
    
    def validate_nuitka_build(self):
        """Comprehensive validation of Nuitka build."""
        validation_tests = [
            self._test_executable_exists,
            self._test_startup_functionality,
            self._test_resource_access,
            self._test_performance_baseline,
        ]
        
        results = {}
        all_passed = True
        
        for test in validation_tests:
            test_name = test.__name__
            try:
                result = test()
                results[test_name] = {'success': True, 'data': result}
                print(f"✓ {test_name}: PASSED")
            except Exception as e:
                results[test_name] = {'success': False, 'error': str(e)}
                print(f"✗ {test_name}: FAILED - {e}")
                all_passed = False
        
        self.validation_results = results
        return all_passed, results
    
    def _test_executable_exists(self):
        """Test that Nuitka executable was created."""
        if not self.nuitka_dir.exists():
            raise FileNotFoundError("Nuitka build directory not found")
        
        # Find the main executable
        possible_names = ['main', 'main.exe', 'LCMSpector', 'LCMSpector.exe']
        for name in possible_names:
            exe_path = self.nuitka_dir / name
            if exe_path.exists():
                return {'executable_path': str(exe_path), 'size_mb': exe_path.stat().st_size / (1024*1024)}
        
        raise FileNotFoundError("No Nuitka executable found")
    
    def _test_startup_functionality(self):
        """Test that the application starts and responds."""
        exe_info = self.validation_results.get('_test_executable_exists', {}).get('data', {})
        exe_path = exe_info.get('executable_path')
        
        if not exe_path:
            raise ValueError("No executable path available")
        
        import time
        start_time = time.perf_counter()
        
        result = subprocess.run(
            [exe_path, '--version'],
            capture_output=True,
            text=True,
            timeout=20
        )
        
        end_time = time.perf_counter()
        startup_time = end_time - start_time
        
        if result.returncode != 0:
            raise RuntimeError(f"Application failed to start: {result.stderr}")
        
        return {'startup_time': startup_time, 'output': result.stdout}
    
    def _test_resource_access(self):
        """Test that resources are properly bundled."""
        exe_info = self.validation_results.get('_test_executable_exists', {}).get('data', {})
        exe_path = exe_info.get('executable_path')
        
        if not exe_path:
            raise ValueError("No executable path available")
        
        result = subprocess.run(
            [exe_path, '--test-resources'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Resource test failed: {result.stderr}")
        
        return {'resources_ok': True, 'output': result.stdout}
    
    def _test_performance_baseline(self):
        """Test that performance meets minimum requirements."""
        startup_data = self.validation_results.get('_test_startup_functionality', {}).get('data', {})
        startup_time = startup_data.get('startup_time', float('inf'))
        
        # Set baseline: should be faster than 10 seconds (very conservative)
        max_acceptable_time = 10.0
        
        if startup_time > max_acceptable_time:
            raise RuntimeError(f"Startup time too slow: {startup_time:.2f}s > {max_acceptable_time}s")
        
        return {'startup_time': startup_time, 'baseline_met': True}
    
    def rollback_to_pyinstaller(self):
        """Rollback to PyInstaller if Nuitka validation fails."""
        if not self.backup_dir.exists():
            raise FileNotFoundError("No PyInstaller backup available for rollback")
        
        # Remove current build
        if self.current_dir.exists():
            shutil.rmtree(self.current_dir)
        
        # Restore from backup
        shutil.copytree(self.backup_dir, self.current_dir)
        
        # Log rollback
        rollback_log = {
            'rollback_date': datetime.now().isoformat(),
            'reason': 'nuitka_validation_failed',
            'validation_results': self.validation_results
        }
        
        with open(self.current_dir / 'rollback_log.json', 'w') as f:
            json.dump(rollback_log, f, indent=2)
        
        return True
    
    def commit_nuitka_build(self):
        """Commit to Nuitka build after successful validation."""
        if not self.nuitka_dir.exists():
            raise FileNotFoundError("No Nuitka build to commit")
        
        # Remove old build
        if self.current_dir.exists():
            shutil.rmtree(self.current_dir)
        
        # Move Nuitka build to current
        shutil.move(str(self.nuitka_dir), str(self.current_dir))
        
        # Save commit metadata
        commit_log = {
            'commit_date': datetime.now().isoformat(),
            'build_system': 'nuitka',
            'validation_results': self.validation_results
        }
        
        with open(self.current_dir / 'build_info.json', 'w') as f:
            json.dump(commit_log, f, indent=2)
        
        # Clean up backup if everything is successful
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        return True

# Usage example
if __name__ == "__main__":
    manager = NuitkaMigrationManager()
    
    # Backup current build
    print("Creating backup of current PyInstaller build...")
    manager.backup_current_build()
    
    # Validate Nuitka build
    print("Validating Nuitka build...")
    success, results = manager.validate_nuitka_build()
    
    if success:
        print("✓ All validation tests passed!")
        print("Committing Nuitka build...")
        manager.commit_nuitka_build()
        print("✓ Migration completed successfully!")
    else:
        print("✗ Validation failed. Rolling back to PyInstaller...")
        manager.rollback_to_pyinstaller()
        print("✓ Rollback completed. PyInstaller build restored.")
```

---

## Build System Integration

### 1. Updated GitHub Actions Workflow
```yaml
# .github/workflows/nuitka-build.yml
name: Build and Release with Nuitka

on:
  workflow_dispatch:
    inputs:
      version:
        description: "Enter the version (e.g., v1.0.0)"
        required: true
      build_system:
        description: "Build system to use"
        required: true
        default: "nuitka"
        type: choice
        options:
          - nuitka
          - pyinstaller

jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest]
        include:
          - os: windows-latest
            executable_name: "main.exe"
            artifact_name: "LCMSpector-${{ github.event.inputs.version }}-Win11-x86_64"
          - os: macos-latest
            executable_name: "LCMSpector.app"
            artifact_name: "LCMSpector-${{ github.event.inputs.version }}-macOS-arm64"

    runs-on: ${{ matrix.os }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          lfs: false
          fetch-depth: 0

      - name: Download MSP library from Polybox
        run: |
          curl -L -o MoNA-export-All_LC-MS-MS_Orbitrap.zip "https://polybox.ethz.ch/index.php/s/CrnWdgwX5canNxL/download"
          unzip -o MoNA-export-All_LC-MS-MS_Orbitrap.zip
          mv MoNA-export-All_LC-MS-MS_Orbitrap.msp lc-inspector/resources/
        shell: bash

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip setuptools wheel
          pip install -r requirements.txt

      - name: Install Nuitka
        if: github.event.inputs.build_system == 'nuitka'
        run: |
          pip install nuitka[full]

      - name: Install PyInstaller (fallback)
        if: github.event.inputs.build_system == 'pyinstaller'
        run: |
          pip install pyinstaller pyinstaller-hooks-contrib

      - name: Build with Nuitka (macOS)
        if: github.event.inputs.build_system == 'nuitka' && matrix.os == 'macos-latest'
        run: |
          cd lc-inspector/
          python -m nuitka \
            --standalone \
            --onefile \
            --enable-plugin=pyqt6 \
            --enable-plugin=numpy \
            --macos-create-app-bundle \
            --macos-app-icon=icon.icns \
            --macos-app-name="LCMSpector" \
            --macos-app-version="${{ github.event.inputs.version }}" \
            --include-data-dir=resources=resources \
            --include-data-file=config.json=config.json \
            --include-data-file=ui/logo.png=ui/logo.png \
            --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm \
            --python-flag=no_site \
            --python-flag=-O \
            --output-dir=dist \
            main.py

      - name: Build with Nuitka (Windows)
        if: github.event.inputs.build_system == 'nuitka' && matrix.os == 'windows-latest'
        run: |
          cd lc-inspector/
          python -m nuitka ^
            --standalone ^
            --onefile ^
            --enable-plugin=pyqt6 ^
            --enable-plugin=numpy ^
            --windows-icon-from-ico=icon.icns ^
            --include-data-dir=resources=resources ^
            --include-data-file=config.json=config.json ^
            --include-data-file=ui/logo.png=ui/logo.png ^
            --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm ^
            --python-flag=no_site ^
            --python-flag=-O ^
            --output-dir=dist ^
            main.py
        shell: cmd

      - name: Build with PyInstaller (Fallback)
        if: github.event.inputs.build_system == 'pyinstaller'
        run: |
          cd lc-inspector/
          pyinstaller LCMSpector.spec

      - name: Run validation tests
        run: |
          pip install pytest
          python -m pytest tests/test_nuitka_build.py -v

      - name: Benchmark performance
        run: |
          python scripts/benchmark_startup.py

      - name: Package for distribution (macOS)
        if: matrix.os == 'macos-latest'
        run: |
          cd lc-inspector/
          if [ "${{ github.event.inputs.build_system }}" = "nuitka" ]; then
            zip -r ../${{ matrix.artifact_name }}.zip dist/LCMSpector.app
          else
            zip -r ../${{ matrix.artifact_name }}.zip dist/LCMSpector.app
          fi

      - name: Package for distribution (Windows)
        if: matrix.os == 'windows-latest'
        run: |
          cd lc-inspector/
          if [ "${{ github.event.inputs.build_system }}" = "nuitka" ]; then
            7z a ../${{ matrix.artifact_name }}.zip dist/main.exe
          else
            7z a ../${{ matrix.artifact_name }}.zip dist/LCMSpector/
          fi
        shell: bash

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact_name }}
          path: ${{ matrix.artifact_name }}.zip
          retention-days: 30

  release:
    needs: build
    runs-on: ubuntu-latest
    if: success()

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Download all build artifacts
        uses: actions/download-artifact@v4
        with:
          merge-multiple: true

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ github.event.inputs.version }}
          name: "Release ${{ github.event.inputs.version }} (${{ github.event.inputs.build_system }})"
          draft: false
          prerelease: false
          body: |
            ## LCMSpector ${{ github.event.inputs.version }}
            
            Built with: **${{ github.event.inputs.build_system }}**
            
            ### Downloads
            - **macOS**: LCMSpector-${{ github.event.inputs.version }}-macOS-arm64.zip
            - **Windows**: LCMSpector-${{ github.event.inputs.version }}-Win11-x86_64.zip
            
            ### Changes
            - Migrated to Nuitka for improved startup performance
            - Enhanced resource bundling system
            - Cross-platform compatibility improvements
          files: |
            LCMSpector-${{ github.event.inputs.version }}-macOS-arm64.zip
            LCMSpector-${{ github.event.inputs.version }}-Win11-x86_64.zip
```

### 2. Local Build Scripts

#### macOS Build Script
```bash
#!/bin/bash
# build_nuitka_macos.sh

set -e

echo "Building LCMSpector with Nuitka for macOS..."

# Change to project directory
cd lc-inspector/

# Ensure dependencies are installed
echo "Installing/updating Nuitka..."
pip install --upgrade nuitka[full]

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/

# Run Nuitka build
echo "Running Nuitka compilation..."
python -m nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyqt6 \
    --enable-plugin=numpy \
    --macos-create-app-bundle \
    --macos-app-icon=icon.icns \
    --macos-app-name="LCMSpector" \
    --macos-app-version="1.0.0" \
    --include-data-dir=resources=resources \
    --include-data-file=config.json=config.json \
    --include-data-file=ui/logo.png=ui/logo.png \
    --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm \
    --python-flag=no_site \
    --python-flag=-O \
    --output-dir=dist \
    --show-progress \
    --assume-yes-for-downloads \
    main.py

echo "Build completed! App bundle created at: dist/LCMSpector.app"

# Validate the build
echo "Validating build..."
if [ -d "dist/LCMSpector.app" ]; then
    echo "✓ App bundle created successfully"
    
    # Check bundle structure
    if [ -f "dist/LCMSpector.app/Contents/MacOS/LCMSpector" ]; then
        echo "✓ Executable found in bundle"
    else
        echo "✗ Executable not found in bundle"
        exit 1
    fi
    
    # Test execution
    echo "Testing app execution..."
    timeout 10s open -a "dist/LCMSpector.app" --args --version || echo "App test completed"
    
else
    echo "✗ App bundle not created"
    exit 1
fi

echo "✓ macOS build validation completed successfully!"
```

#### Windows Build Script
```batch
@echo off
REM build_nuitka_windows.bat

echo Building LCMSpector with Nuitka for Windows...

cd lc-inspector\

REM Ensure dependencies are installed
echo Installing/updating Nuitka...
pip install --upgrade nuitka[full]

REM Clean previous builds
echo Cleaning previous builds...
if exist dist\ rmdir /s /q dist\
if exist build\ rmdir /s /q build\

REM Run Nuitka build
echo Running Nuitka compilation...
python -m nuitka ^
    --standalone ^
    --onefile ^
    --enable-plugin=pyqt6 ^
    --enable-plugin=numpy ^
    --windows-icon-from-ico=icon.icns ^
    --windows-company-name="ETH Zurich" ^
    --windows-product-name="LCMSpector" ^
    --windows-file-version="1.0.0" ^
    --windows-product-version="1.0.0" ^
    --include-data-dir=resources=resources ^
    --include-data-file=config.json=config.json ^
    --include-data-file=ui/logo.png=ui/logo.png ^
    --nofollow-import-to=matplotlib,torch,torchvision,frozendict,tqdm ^
    --python-flag=no_site ^
    --python-flag=-O ^
    --output-dir=dist ^
    --show-progress ^
    --assume-yes-for-downloads ^
    main.py

echo Build completed! Executable created at: dist\main.exe

REM Validate the build
echo Validating build...
if exist "dist\main.exe" (
    echo ✓ Executable created successfully
    
    REM Test execution
    echo Testing executable...
    timeout /t 5 /nobreak >nul
    "dist\main.exe" --version
    
    if errorlevel 1 (
        echo ✗ Executable test failed
        exit /b 1
    ) else (
        echo ✓ Executable test passed
    )
) else (
    echo ✗ Executable not created
    exit /b 1
)

echo ✓ Windows build validation completed successfully!
```

---

## Implementation Timeline and Milestones

### Week 1: Setup and Configuration
- **Day 1-2**: Set up Nuitka development environment
- **Day 3-4**: Create basic Nuitka configuration
- **Day 5**: Test initial build on both platforms

### Week 2: Resource Handling and Optimization
- **Day 1-2**: Implement resource bundling strategy
- **Day 3-4**: Optimize for large MS library file
- **Day 5**: Cross-platform testing

### Week 3: Testing and Validation
- **Day 1-2**: Implement automated test suite
- **Day 3-4**: Performance benchmarking
- **Day 5**: Integration testing

### Week 4: CI/CD and Deployment
- **Day 1-2**: Update GitHub Actions workflows
- **Day 3-4**: Create deployment packages
- **Day 5**: Final validation and documentation

## Success Criteria

### Performance Targets
- **Startup Time**: 40-70% reduction vs PyInstaller
- **Memory Usage**: No more than 10% increase
- **Binary Size**: Comparable to current PyInstaller build

### Functional Requirements
- ✓ All GUI features working
- ✓ File loading and processing intact
- ✓ Cross-platform compatibility maintained
- ✓ All current features preserved

### Quality Metrics
- ✓ Automated test suite passes 100%
- ✓ No regression in functionality
- ✓ Successful CI/CD pipeline execution
- ✓ Clean rollback capability if needed

---

This plan provides a comprehensive roadmap for migrating LC-Inspector from PyInstaller to Nuitka, with clear technical specifications, testing frameworks, and risk mitigation strategies.