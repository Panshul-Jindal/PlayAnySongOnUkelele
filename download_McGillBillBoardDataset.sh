"Download the McGill Billboard Dataset.

Source: https://ddmal.ca/research/The_McGill_Billboard_Project_(Chord_Analysis_Dataset)/
"

mkdir -p data/McGillBillboard
cd data/McGillBillboard
wget https://www.dropbox.com/s/o0olz0uwl9z9stb/billboard-2.0-index.csv
wget https://www.dropbox.com/s/2lvny9ves8kns4o/billboard-2.0-salami_chords.tar.gz
wget https://www.dropbox.com/s/ep41gwy28vo3wxy/billboard-2.0.1-lab.tar.gz
wget https://www.dropbox.com/s/f88s73bmivlvbiy/billboard-2.0.1-mirex.tar.gz
wget https://www.dropbox.com/s/8g8z6cgt6w1yosv/billboard-2.0-echonest.tar.gz


tar -xvzf billboard-2.0-salami_chords.tar.gz
tar -xvzf billboard-2.0.1-lab.tar.gz
tar -xvzf billboard-2.0.1-mirex.tar.gz
tar -xvzf billboard-2.0-echonest.tar.gz 
