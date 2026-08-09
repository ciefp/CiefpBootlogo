import os
import subprocess
from PIL import Image
import shutil


def convert_to_mvi(image_path, resolution="FHD"):
    """
    Konvertuje sliku u .mvi format za Enigma2
    """
    try:
        if not os.path.exists(image_path):
            return False, "Slika ne postoji"

        resolutions = {
            "HD": (1280, 720),
            "FHD": (1920, 1080),
            "UHD": (3840, 2160)
        }

        width, height = resolutions.get(resolution, (1920, 1080))

        # Otvori i pripremi sliku preko PIL-a
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        img = img.resize((width, height), Image.Resampling.LANCZOS)

        base_name = os.path.splitext(os.path.basename(image_path))[0]
        mvi_path = "/tmp/" + base_name + ".mvi"
        bmp_path = "/tmp/" + base_name + ".bmp"

        img.save(bmp_path, 'BMP')

        # Obavezna konverzija preko FFmpeg u MPEG-2 ES (.mvi format)
        if shutil.which('ffmpeg'):
            cmd = [
                'ffmpeg', '-y', '-i', bmp_path,
                '-vcodec', 'mpeg2video',
                '-q:v', '2',
                '-f', 'm2v',
                mvi_path
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                return False, "FFmpeg greška: " + result.stderr.decode()
        else:
            return False, "FFmpeg nije instaliran na sistemu! Instalirajte ffmpeg paket."

        # Instalacija u sistem
        dest_path = "/usr/share/bootlogo.mvi"

        if os.path.exists(dest_path):
            backup_path = "/usr/share/bootlogo_backup.mvi"
            shutil.copy2(dest_path, backup_path)

        shutil.copy2(mvi_path, dest_path)

        # Čišćenje privremenih fajlova
        if os.path.exists(bmp_path):
            os.remove(bmp_path)
        if os.path.exists(mvi_path):
            os.remove(mvi_path)

        return True, "Bootlogo uspješno instaliran na " + dest_path

    except Exception as e:
        return False, str(e)

def check_ffmpeg():
    """Provjeri da li je ffmpeg instaliran"""
    return shutil.which('ffmpeg') is not None
    
def get_image_info(image_path):
    """Dohvati informacije o slici"""
    try:
        img = Image.open(image_path)
        return {
            'width': img.width,
            'height': img.height,
            'format': img.format,
            'mode': img.mode
        }
    except:
        return None