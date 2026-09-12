Name:           luajit-luarocks
# -cache dir. Bug in %post
%global lr_lua_version 5.1
%global lr_lua_id jit
%global lr_debug 1
Version:        3.13.0
Release:        3.2%{?dist}
Summary:        A deployment and management system for Lua modules

License:        MIT
URL:            http://luarocks.org

# lpeg_rock version-names
%global lpeg_rock lpeg-1.1.0-2
#global lpeg_dir lpeg-1.1.0
%global lpeg_dir %{lua:print((rpm.expand("%{lpeg_rock}"):gsub("%-%d+$", "")))}
%global lpeg_version %{lua:print((rpm.expand("%{lpeg_dir}"):gsub("^lpeg%-", "")))}
%global lpeg_rock_file %{lpeg_rock}.src.rock
%global lpeg_rock_dir %{_datadir}/luarocks-%{lr_lua_id}

Source0:        http://luarocks.org/releases/luarocks-%{version}.tar.gz
Source1:        https://luarocks.org/%{lpeg_rock_file}

# Use /usr/lib64 as default LUA_LIBDIR
Patch0:         luarocks-3.9.1-dynamic_libdir.patch
Patch1:         luarocks-3.13.0-configure_GNUmakefile_cfg.patch
Patch2:         luarocks-3.13.0-config-explicit-LUA.patch
Patch3:         luarocks-3.13.0-manifest_jit.patch

BuildArch:      noarch
# # luarocks-5.1 -has- had the same binary/folder names
# Conflicts:      luarocks-5.1

BuildRequires:  luajit-devel
BuildRequires:  make
%if 0%{?el7}
BuildRequires:  lua-rpm-macros
%endif
Requires:       luajit
Requires:       unzip
Requires:       zip
Requires:       gcc

%if 0%{?fedora}
Recommends:     lua-sec
Recommends:     lua-devel
Recommends:     compat-lua-devel
Recommends:     make
Recommends:     cmake
%endif


%description
LuaRocks allows you to install Lua modules as self-contained packages
called "rocks", which also contain version dependency
information. This information is used both during installation, so
that when one rock is requested all rocks it depends on are installed
as well, and at run time, so that when a module is required, the
correct version is loaded. LuaRocks supports both local and remote
repositories, and multiple local rocks trees.


%prep
%autosetup -n luarocks-%{version} -p1


%build
./configure \
  --prefix=%{_prefix} \
  --lua-version=%{lr_lua_version} \
  --with-lua=%{_prefix} \
  --config-filename=config-%{lr_lua_id}.lua \
  --local-dirname=.luarocks-%{lr_lua_id} \
  --rocks-subdir=lib/luarocks/rocks-%{lr_lua_id} \
  --luarocks-rocks=%{_prefix}/share/lua/%{lr_lua_id} \
  --with-lua-include=%{_includedir}/luajit-2.1 \
  --with-lua-interpreter=luajit

%make_build

%install
%make_install

mkdir -p %{buildroot}%{_prefix}/lib/luarocks/rocks-%{lr_lua_id}
mv %{buildroot}%{_bindir}/luarocks{,-%{lr_lua_id}}
mv %{buildroot}%{_bindir}/luarocks-admin{,-%{lr_lua_id}}
mkdir -pv %{buildroot}%{_datadir}/lua/%{lr_lua_id}
%if 0%{?lr_debug}
pwd; find . -name 'config-*.lua' #; sleep 10
%endif

mkdir -p %{buildroot}%{lpeg_rock_dir}
install -m 0644 %{SOURCE1} %{buildroot}%{lpeg_rock_dir}/%{lpeg_rock_file}


%check
# TODO ? If you want to do it here after compile, you are welcome.
# The required LPeg build is performed after installation and is a perfect check
# See below: %post


%files
%license COPYING
%doc README.md
%config(noreplace) %{_sysconfdir}/luarocks/config-%{lr_lua_id}.lua
%{_bindir}/luarocks-%{lr_lua_id}
%{_bindir}/luarocks-admin-%{lr_lua_id}
%{_datadir}/lua/%{lr_lua_id}/luarocks
%{lpeg_rock_dir}/%{lpeg_rock_file}
%{_datadir}/lua/%{lr_lua_id}/compat53


%post
clean_(){ rm -rf "$tmpdir"; exit "$1"; }
set -e
printf 'NOTICE: %%%%post %s: See /tmp/%{name}.dbg.log\n' "$(date -Im)" | tee -a "/tmp/%{name}.dbg.log"
%if 0%{?lr_debug}
set -x
exec >> "/tmp/%{name}.dbg.log" 2>&1
%else
exec >> /dev/null 2>&1 # Comment out for verbose script run on install terminal
%endif
trap 'clean_ $?' EXIT
tmpdir="$(mktemp -d)" && [ -d "$tmpdir" ]
unzip -q %{lpeg_rock_dir}/%{lpeg_rock_file} -d "$tmpdir"
tar -xf "$tmpdir/%{lpeg_dir}.tar.gz" -C "$tmpdir"
cd "$tmpdir/%{lpeg_dir}"
/usr/bin/luarocks-%{lr_lua_id} build ../%{lpeg_rock}.rockspec \
%if 0%{?lr_debug}
  2>&1
%else
  >>/dev/null 2>&1
%endif
# above %if placed here if line 4 is commented out

%preun
set -e
printf 'NOTICE: %%%%preun %s: See /tmp/%{name}.dbg.log\n' "$(date -Im)" | tee -a "/tmp/%{name}.dbg.log"
%if 0%{?lr_debug}
set -x
exec >> "/tmp/%{name}.dbg.log" 2>&1
%else
exec >> /dev/null 2>&1 # Comment out for verbose script run on install terminal
%endif
set -e
if [ "$1" -eq 0 ]; then
%if 0%{?lr_debug}
  rm -rfv %{_prefix}/lib/luarocks/rocks-%{lr_lua_id}/lpeg/
%else
  rm -rfv %{_prefix}/lib/luarocks/rocks-%{lr_lua_id}/lpeg/
%endif
fi


%posttrans
%if 0%{?lr_debug}
luarocks-%{lr_lua_id} --global list
%else
luarocks-%{lr_lua_id} --global list | grep -F "(installed) - %{_prefix}/lib/luarocks/rocks-%{lr_lua_id}"
%endif
luajit -e 'local lpeg = require("lpeg"); print("LPeg loaded:", lpeg.version)'
printf 'NOTICE: LuaRocks remote manifest initial download and search can be run\n'\
'        manually by> sudo luarocks-%{lr_lua_id} --global search lpeg %{lpeg_version}\n'\
'                 or> luarocks-%{lr_lua_id} search lpeg %{lpeg_version}'


%changelog
* %{lua:print(os.date("%a %b %d %Y"))} Nordic PA <nordicpa@gmail.com> - %{version}-%{release}
- Package name change from luarocks to %{name}
- Add support for luajit 5.1 binary
- Add support for rocks-jit coexisting with rocks-5.1
- Fix LuaRocks manifest failure with more than 65,536 constants (bug #1797)
- Designed 'configure' to coexist with any and all luarocks versions and lua versions
- Spawned from source build below for standard Fedora luarocks

* Thu Jul 16 2026 Fedora Release Engineering <releng@fedoraproject.org> - 3.13.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_45_Mass_Rebuild

* Tue May  5 2026 Tom Callaway <spot@fedoraproject.org> - 3.13.0-2
- rebuild

* Tue Feb 17 2026 Tom Callaway <spot@fedoraproject.org> - 3.13.0-1
- update to 3.13.0
- built against lua 5.5.0

* Fri Jan 16 2026 Fedora Release Engineering <releng@fedoraproject.org> - 3.9.2-9
- Rebuilt for https://fedoraproject.org/wiki/Fedora_44_Mass_Rebuild
