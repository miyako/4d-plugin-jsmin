# 4d-plugin-jsmin
4D port of [JSMin](https://github.com/douglascrockford/JSMin) by Douglas Crockford 

###Platform

| carbon | cocoa | win32 | win64 |
|:------:|:-----:|:---------:|:---------:|
|🆗|🆗|🆗|🆗|

###Version

<img src="https://cloud.githubusercontent.com/assets/1725068/18940649/21945000-8645-11e6-86ed-4a0f800e5a73.png" width="32" height="32" /> <img src="https://cloud.githubusercontent.com/assets/1725068/18940648/2192ddba-8645-11e6-864d-6d5692d55717.png" width="32" height="32" />

###Syntax

param|type|description
------------|------|----
src|TEXT|code to minify 
dst|TEXT|minified code

Example
---

```
$path:=Get 4D folder(Current resources folder)+"jquery.js"
$src:=Document to text($path;"utf-8")
$dst:=JSMin ($src)
SET TEXT TO PASTEBOARD($dst)
```
