#!/bin/bash
# mk_patches.sh

PATCHES0='
luarocks-3.9.1-dynamic_libdir.patch	src/luarocks/core/cfg.lua
'
PATCHES='
luarocks-3.13.0-configure_GNUmakefile_cfg.patch	configure
luarocks-3.13.0-configure_GNUmakefile_cfg.patch	GNUmakefile
luarocks-3.13.0-configure_GNUmakefile_cfg.patch	src/luarocks/core/cfg.lua
luarocks-3.13.0-search_lua-interpreter.patch	src/luarocks/cmd.lua
luarocks-3.13.0-search_lua-interpreter.patch	src/luarocks/util.lua
luarocks-3.13.0-manifest_jit.patch	src/luarocks/core/manif.lua
luarocks-3.13.0-manifest_jit.patch	src/luarocks/core/manifest_jit.lua
'
mk_patches() {
  [ "$1" = -0 ] && {
    rm -rfv a | tail -n3
    rm -rfv luarocks-3.13.0/ | tail -n3
    tar xf luarocks-3.13.0.tar.gz
    cp -va luarocks-3.13.0 a | tail -n3
    while read -r p f; do
      eval "$(printf 'p="%s"    f="%s"\n' "$p" "$f")"
      [ "$p" ] || continue
      [ -r a/"$f" ] || touch a/"$f"
      (
        cd a
        pwd
        echo "patch -p1 <<<../$p"
        patch -p1 <../"$p"
      )
    done <<<"$PATCHES0"
    printf 'Create changes before you run again as >  %s/%s\n' "$(pwd)" "$0"
    return
  }
  (
    op=''
    IFS=$'\t'
    while read -r p f; do
      eval "$(printf 'p="%s"    f="%s"\n' "$p" "$f")"
      [ "$p" ] || continue
      [ "$p" = "$op" ] || cp /dev/null "$p"2
      [ -r a/"$f" ] || touch a/"$f" # -- not -- [ -r b/"$f" ] || touch b/"$f"
      diff -ua a/"$f" b/"$f" | sed '/^[+-][+-][+-] /{s|\t.*||}' >>"$p"2
      op="$p"
    done <<<"$PATCHES"
  )
}

mk_patches "$@"
