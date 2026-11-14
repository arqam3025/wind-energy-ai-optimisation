#!/usr/bin/env bash
# Download the pinned Kelmarsh record (Zenodo 10.5281/zenodo.16807551, CC-BY-4.0) and verify the
# published MD5 of every file. Sealed test years (2023, 2024) are downloaded and verified but
# NEVER extracted here; extraction is allowed only after a real-data protocol is frozen.
set -euo pipefail
ROOT="${1:-C:/ResearchData/kelmarsh_zenodo_16807551}"
BASE="https://zenodo.org/records/16807551/files"
fetch() {  # dir file md5
  local dir="$ROOT/$1" file="$2" md5="$3"
  if [ -f "$dir/$file" ] && [ "$(md5sum "$dir/$file" | cut -d' ' -f1)" = "$md5" ]; then
    echo "ok (cached) $1/$file"; return
  fi
  curl -fsSL --retry 5 --retry-delay 10 -o "$dir/$file.part" "$BASE/$file?download=1"
  local got; got="$(md5sum "$dir/$file.part" | cut -d' ' -f1)"
  if [ "$got" != "$md5" ]; then echo "MD5 MISMATCH $file: $got != $md5" >&2; rm -f "$dir/$file.part"; exit 1; fi
  mv "$dir/$file.part" "$dir/$file"; echo "ok $1/$file"
}
fetch metadata    Kelmarsh_WT_static.csv            af3a038f0f7fddfc1608ad0bfc8cf5ba
fetch metadata    Kelmarsh_WT_dataSignalMapping.csv ca8fe399ab15ae7111d3214c632efd36
fetch metadata    Kelmarsh_Grid_Meter_4458.zip      2696caad88ea08ac22e5fa00da9c3c46
fetch development Kelmarsh_SCADA_2018_3084.zip      972e5280172216a5fe76dcab19c741b0
fetch development Kelmarsh_SCADA_2019_3085.zip      14348a1572b722e1be10e53cd145c39a
fetch development Kelmarsh_SCADA_2020_3086.zip      e189e02da98f32e74acc72e8559ef0db
fetch development Kelmarsh_SCADA_2021_4456.zip      4e0ef3d65f067fd3d8f3d30e79ab01ae
fetch validation  Kelmarsh_SCADA_2022_4457.zip      b695d2b21cd5a236b2e690e0a43df5ab
fetch sealed_test Kelmarsh_SCADA_2023_5961.zip      685d9589347d1866f6f2cfe45b9af4f4
fetch sealed_test Kelmarsh_SCADA_2024_5962.zip      e9e3318f5b393d8596ff1801f8da0414
echo "ALL FILES VERIFIED"
