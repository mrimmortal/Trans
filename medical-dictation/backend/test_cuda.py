# test_cuda_venv.py
import os
import sys
import glob

print("=" * 60)
print("CUDA Setup Test for Virtual Environment")
print("=" * 60)

# Apply the same CUDA fix
if sys.platform == "win32":
    try:
        site_packages_dirs = [p for p in sys.path if 'site-packages' in p.lower()]
        
        if not site_packages_dirs:
            raise ImportError("site-packages not found")
        
        site_packages = site_packages_dirs[0]
        nvidia_base = os.path.join(site_packages, 'nvidia')
        
        print(f"\n📁 Virtual Environment:")
        print(f"   Python: {sys.executable}")
        print(f"   Site-packages: {site_packages}")
        print(f"   NVIDIA base: {nvidia_base}")
        
        if not os.path.exists(nvidia_base):
            raise ImportError(f"nvidia directory not found at {nvidia_base}")
        
        # Find all CUDA paths
        cuda_paths = []
        
        for subdir in ['cublas', 'cudnn']:
            base_dir = os.path.join(nvidia_base, subdir)
            if os.path.exists(base_dir):
                for root, dirs, files in os.walk(base_dir):
                    dll_files = [f for f in files if f.endswith('.dll')]
                    if dll_files and root not in cuda_paths:
                        cuda_paths.append(root)
        
        if cuda_paths:
            print(f"\n✓ Found {len(cuda_paths)} CUDA path(s):")
            for p in cuda_paths:
                dll_count = len(glob.glob(os.path.join(p, '*.dll')))
                print(f"  - {p} ({dll_count} DLLs)")
            
            # Add to PATH
            path_addition = os.pathsep.join(cuda_paths)
            os.environ['PATH'] = path_addition + os.pathsep + os.environ.get('PATH', '')
            
            print(f"\n✓ Added to system PATH")
        else:
            raise ImportError("No CUDA DLL directories found")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

# Now test imports
print("\n" + "=" * 60)
print("Testing CUDA Libraries")
print("=" * 60)

try:
    import torch
    print(f"\n✓ PyTorch imported")
    print(f"  CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  CUDA version: {torch.version.cuda}")
except ImportError as e:
    print(f"\n✗ PyTorch import failed: {e}")

try:
    from faster_whisper import WhisperModel
    print(f"\n✓ Faster-Whisper imported")
    
    # Try to load model on CUDA
    print(f"\n🔄 Testing model load on CUDA...")
    model = WhisperModel("tiny", device="cuda", compute_type="float16")
    print(f"✓ Model loaded successfully on GPU!")
    
    # Test transcription
    import numpy as np
    dummy_audio = np.zeros(16000, dtype=np.float32)
    segments, info = model.transcribe(dummy_audio)
    list(segments)  # Consume generator
    print(f"✓ Transcription test passed!")
    
    print("\n" + "=" * 60)
    print("🎉 SUCCESS! CUDA is working correctly!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nTrying CPU mode...")
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print(f"✓ CPU mode works")
    except Exception as cpu_error:
        print(f"✗ CPU mode also failed: {cpu_error}")