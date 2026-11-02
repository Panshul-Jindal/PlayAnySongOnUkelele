#!/bin/sh
# Download the ukulele chord chart of chords-db (MIT licence), pinned to one
# commit, and check that the files are the ones the project was built against.
#
# Source: https://github.com/tombatossals/chords-db

set -e
COMMIT=df06fa7b425cf5fd29485ff6591236b3557e3fac
URL=https://raw.githubusercontent.com/tombatossals/chords-db/$COMMIT

mkdir -p data/chords-db
wget -q -O data/chords-db/ukulele.json "$URL/lib/ukulele.json"
wget -q -O data/chords-db/LICENSE "$URL/LICENSE"

sha256sum -c <<EOF
233b7018ec35785a8bfa985bad90f4745cee04614c0fd1d5b819cff7406ec601  data/chords-db/ukulele.json
ca1f5a79ed75347924bba07c979bc7a6d0f7438e82d655f7e8dcdfa32939a3d9  data/chords-db/LICENSE
EOF
