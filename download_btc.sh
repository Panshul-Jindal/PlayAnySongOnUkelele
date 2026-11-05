#!/bin/sh
# Download BTC's trained weights (MIT licence), pinned to one commit of the
# official repository, and check that the files are the ones the project was
# built against. The model code itself is vendored in chord-estimation/BTC-ISMIR19/.
#
# Source: https://github.com/jayg996/BTC-ISMIR19 (Park, Choi, Jeon, Kim & Park, ISMIR 2019)

set -e
COMMIT=2682317be668032e6e4b269ded36adaa2ad57df0
URL=https://raw.githubusercontent.com/jayg996/BTC-ISMIR19/$COMMIT

mkdir -p data/models/btc
wget -q -O data/models/btc/btc_model.pt "$URL/test/btc_model.pt"
wget -q -O data/models/btc/btc_model_large_voca.pt "$URL/test/btc_model_large_voca.pt"
wget -q -O data/models/btc/LICENSE "$URL/LICENSE"

sha256sum -c <<EOF
71c2c5db17e8c43b8a9a9da5db36ef2d667158c07a214eba16344c154c00bf54  data/models/btc/btc_model.pt
1673d23f8f9a55ae7f9e8b80a51da616debb22675b8d8b67ea6ce0ef37b0ab51  data/models/btc/btc_model_large_voca.pt
7439cc22ff2efee600131dc5d800ab1204d8076a1a815d842a0319782520fc85  data/models/btc/LICENSE
EOF
