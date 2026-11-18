#!/usr/bin/env bash
# Download the pinned Penmanshiel record (Zenodo 10.5281/zenodo.16807304, CC-BY-4.0), WT11-15 group,
# and verify every published MD5. Sealed test years (2023, 2024) are downloaded and verified only;
# they are read solely by the frozen Stage 5 protocol runner.
set -euo pipefail
ROOT="${1:-C:/ResearchData/penmanshiel_zenodo_16807304}"
BASE="https://zenodo.org/records/16807304/files"
mkdir -p "$ROOT"/{metadata,development,validation,sealed_test}
fetch() {  # dir file md5
  local dir="$ROOT/$1" file="$2" md5="$3"
  if [ -f "$dir/$file" ] && [ "$(md5sum "$dir/$file" | cut -d' ' -f1)" = "$md5" ]; then echo "ok (cached) $1/$file"; return; fi
  local enc="${file// /%20}" attempt
  for attempt in 1 2 3 4 5 6 7 8; do
    if curl -fsSL -C - --retry 5 --retry-all-errors --retry-delay 10 -o "$dir/$file.part" "$BASE/$enc?download=1"; then break; fi
    echo "retrying $file (attempt $attempt)" >&2; sleep 15
  done
  local got; got="$(md5sum "$dir/$file.part" | cut -d' ' -f1)"
  if [ "$got" != "$md5" ]; then echo "MD5 MISMATCH $file: $got != $md5" >&2; rm -f "$dir/$file.part"; exit 1; fi
  mv "$dir/$file.part" "$dir/$file"; echo "ok $1/$file"
}
fetch metadata    Penmanshiel_WT_static.csv                c4cd4191234c1a67a391fe5d2978256b
fetch development Penmanshiel_SCADA_2018_WT11-15_3116.zip  7c40dc00df6d6301427213e15170b927
fetch development Penmanshiel_SCADA_2019_WT11-15_3117.zip  92747a976716c5f35d9ee6462958fd7a
fetch development Penmanshiel_SCADA_2020_WT11-15_3118.zip  c73323f21451c08247dbdb5d1a1434a9
fetch development Penmanshiel_SCADA_2021_WT11-15_4461.zip  f5804b90089ce4d50dc5117fda6f675c
fetch validation  Penmanshiel_SCADA_2022_WT11-15_4463.zip  5f4743133a9cf65ad33de139b43f96b4
fetch sealed_test Penmanshiel_SCADA_2023_WT_11-15_5964.zip 813ad4635cf50b9d96b253ee53175086
fetch sealed_test Penmanshiel_SCADA_2024_WT_11-15_5966.zip e0a700cad1d45f4130272feaef244b12
echo "ALL FILES VERIFIED"
