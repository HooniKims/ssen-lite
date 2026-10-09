'use strict';
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
execFileSync('cargo',['build','--locked','--release','--manifest-path','native/Cargo.toml'],{cwd:root,stdio:'inherit',windowsHide:true});
fs.mkdirSync(path.join(root,'native/bin'),{recursive:true});
fs.copyFileSync(path.join(root,'native/target/release/ssen-hwpx.exe'),path.join(root,'native/bin/ssen-hwpx.exe'));
