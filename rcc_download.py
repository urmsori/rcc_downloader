from typing import List
import urllib.request
import urllib.parse
import os
import tarfile
import sys
import threading
import time
import shutil

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(f"{CURRENT_DIR}/..")

if len(sys.argv) >= 2:
    rcc_url = sys.argv[1]
else:
    rcc_url = "https://www.gaisler.com/anonftp/rcc/rcc-1.3/1.3.1/sparc-rtems-5-gcc-10.2.0-1.3.1-linux.txz"

if len(sys.argv) >= 3:
    download_segment_num = int(sys.argv[2])
else:
    download_segment_num = 8

rcc_directory = f"{PROJECT_DIR}/rcc"
temp_file_directory = f"{rcc_directory}/temp"
rcc_file_path = f"{temp_file_directory}/{os.path.basename(urllib.parse.urlparse(rcc_url).path)}"

if os.path.exists(temp_file_directory):
    shutil.rmtree(temp_file_directory)
os.makedirs(temp_file_directory)


class DownloadThread(threading.Thread):
    def __init__(self, url, start_pos, end_pos, output_file, progress):
        threading.Thread.__init__(self)
        self.url = url
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.output_file = output_file
        self.progress = progress

    def run(self):
        print(f"Downloading '{self.url}' bytes {self.start_pos}-{self.end_pos} to '{self.output_file}'...")
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.start_pos}-{self.end_pos}'})
        with urllib.request.urlopen(req) as response, open(self.output_file, 'wb') as outfile:
            chunk_size = 1024 * 1024  # 1MB
            bytes_downloaded = 0
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                outfile.write(chunk)
                bytes_downloaded += len(chunk)
                self.progress[self.output_file] = bytes_downloaded
        print(f"Download of '{self.url}' bytes {self.start_pos}-{self.end_pos} to '{self.output_file}' complete.")


# Get the size of the file
file_size = int(urllib.request.urlopen(rcc_url).info().get('Content-Length', -1))

# Calculate the size of each part
part_size = file_size // download_segment_num

# Create a list of DownloadThread instances for each part
threads: List[DownloadThread] = []
progress = {}
for i in range(download_segment_num):
    start_pos = i * part_size
    end_pos = start_pos + part_size - 1
    if i == download_segment_num - 1:
        end_pos = file_size - 1
    output_file = f"{temp_file_directory}/part{i}.zip"
    threads.append(DownloadThread(rcc_url, start_pos, end_pos, output_file, progress))

for thread in threads:
    thread.start()

# Start the threads and periodically print the progress
while any(thread.is_alive() for thread in threads):
    for thread in threads:
        if thread.output_file in progress:
            bytes_downloaded = progress[thread.output_file]
            percent_complete = bytes_downloaded / (thread.end_pos - thread.start_pos + 1) * 100
            print(f"{thread.output_file}: {percent_complete:.2f}% complete")
    print()
    time.sleep(1)

for thread in threads:
    thread.join()

# Combine the downloaded parts into a single file
with open(rcc_file_path, 'wb') as outfile:
    for i in range(download_segment_num):
        part_file = f"{temp_file_directory}/part{i}.zip"
        with open(part_file, 'rb') as infile:
            outfile.write(infile.read())
        os.remove(part_file)

print("Download of '%s' complete." % rcc_url)

print("Start Extract")
with tarfile.open(rcc_file_path, 'r:xz') as tar:
    tar.extractall(path=rcc_directory)
print("End Extract")
