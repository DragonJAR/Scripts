#!/usr/bin/env bash
set -euo pipefail

domain=""
while getopts "d:" opt; do
  case $opt in
    d) domain=$OPTARG ;;
    *) echo "uso: $0 -d <dominio>" >&2; exit 1 ;;
  esac
done

[ -z "$domain" ] && { echo "uso: $0 -d <dominio>" >&2; exit 1; }

curl -s "http://web.archive.org/cdx/search/cdx?url=*.${domain}/*&output=text&fl=original&collapse=urlkey" \
  | sort \
  | sed -e 's_https*://__' -e "s/\/.*//" -e 's/:.*//' -e 's/^www\.//' \
  | uniq