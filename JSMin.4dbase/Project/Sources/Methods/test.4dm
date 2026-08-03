//%attributes = {}
$path:=Get 4D folder:C485(Current resources folder:K5:16)+"jquery.js"
//$path:=System folder(Desktop)+"dlg0_001.js"
$src:=Document to text:C1236($path; "utf-8")
$start:=Milliseconds:C459
$dst:=JSMin($src)
$duration:=Milliseconds:C459-$start
SET TEXT TO PASTEBOARD:C523($dst)