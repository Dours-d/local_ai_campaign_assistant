function Get-LevenshteinDistance {
    param ([string]$s, [string]$t)
    $n = $s.Length
    $m = $t.Length
    $d = New-Object 'int[,]' ($n + 1), ($m + 1)

    if ($n -eq 0) { return $m }
    if ($m -eq 0) { return $n }

    for ($i = 0; $i -le $n; $i++) { $d[$i, 0] = $i }
    for ($j = 0; $j -le $m; $j++) { $d[0, $j] = $j }

    for ($i = 1; $i -le $n; $i++) {
        for ($j = 1; $j -le $m; $j++) {
            $cost = if ($s[$i - 1] -eq $t[$j - 1]) { 0 } else { 1 }
            $d[$i, $j] = [Math]::Min(
                [Math]::Min($d[$i - 1, $j] + 1, $d[$i, $j - 1] + 1),
                $d[$i - 1, $j - 1] + $cost
            )
        }
    }
    return $d[$n, $m]
}

$a = "kitten"
$b = "sitting"
$dist = Get-LevenshteinDistance $a $b
Write-Host "Distance between '$a' and '$b' is $dist (Type: $($dist.GetType().Name))"

if ($dist -eq 3) { Write-Host "Test Passed" } else { Write-Host "Test Failed" }
