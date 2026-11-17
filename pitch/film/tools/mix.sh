#!/usr/bin/env bash
# Builds assets/audio/vo.wav (Davis, each line at its start time) and assets/audio/bed.wav (music looped to 62 s,
# ducked under the voice). Run from the project root: bash tools/mix.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p assets/audio
DUR=62

# ---- voice: one input per line, delayed to its start ----
inputs=(); filters=""; n=0
while IFS=$'\t' read -r id start max text; do
  [[ -z "$id" || "$id" == \#* ]] && continue
  inputs+=(-i "voice/lines/$id.wav")
  ms=$(python3 -c "print(int(float('$start')*1000))")
  filters+="[$n:a]adelay=${ms}|${ms},apad[a$n];"
  n=$((n+1))
done < voice/placement.tsv
mixin=""; for ((i=0;i<n;i++)); do mixin+="[a$i]"; done
ffmpeg -v error -y "${inputs[@]}" -filter_complex "${filters}${mixin}amix=inputs=$n:normalize=0,atrim=0:$DUR,loudnorm=I=-16:TP=-1.5:LRA=11" \
  -ar 48000 -ac 2 assets/audio/vo.wav

# ---- music: take-1 looped with crossfades, faded, 62 s ----
ffmpeg -v error -y -i assets/music/take-1.wav -i assets/music/take-1.wav -i assets/music/take-1.wav \
  -filter_complex "[0][1]acrossfade=d=2:c1=tri:c2=tri[x];[x][2]acrossfade=d=2:c1=tri:c2=tri,atrim=0:$DUR,afade=t=in:d=1.2,afade=t=out:st=$((DUR-3)):d=3,loudnorm=I=-24:TP=-3:LRA=11" \
  -ar 48000 -ac 2 assets/audio/bed-raw.wav

# ---- duck the music under the voice ----
ffmpeg -v error -y -i assets/audio/bed-raw.wav -i assets/audio/vo.wav \
  -filter_complex "[0][1]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=450:makeup=1[d]" -map "[d]" \
  -ar 48000 -ac 2 assets/audio/bed.wav
rm assets/audio/bed-raw.wav
echo "vo + bed written"
