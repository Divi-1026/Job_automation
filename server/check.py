import os
import psutil
from sentence_transformers import SentenceTransformer

process = psutil.Process(os.getpid())

def show_ram(label):
    ram = process.memory_info().rss / (1024 * 1024)
    print(f"{label}: {ram:.2f} MB")

show_ram("Before model loading")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
show_ram("After model loading")

model.encode(["Software developer job matching resume"])
show_ram("After generating embedding")