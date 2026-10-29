import autochord

chords = autochord.recognize(
    "/home/panshul/AI/projects/PlayAnySongOnUkelele/data/Songs/Idina Menzel - Let It Go (From FrozenSing-Along).mp3"
)

for start, end, chord in chords:
    print(f"{start:7.2f}s - {end:7.2f}s : {chord}")