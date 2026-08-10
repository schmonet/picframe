<#
.SYNOPSIS
    Corrects file dates for a photo/video archive based on EXIF metadata, falling back
    to the year encoded in the containing folder name when no metadata is available.

.DESCRIPTION
    Windows PowerShell port of check_pic_dates.sh. Priority order:
      1. Trust EXIF/metadata capture date (DateTimeOriginal / CreateDate / MediaCreateDate)
         when present - most accurate source. If its year disagrees with the folder the
         file is currently filed under, offers to move it into the matching year folder.
      2. If no metadata exists at all, fall back to the year encoded in the folder name
         (the manual sorting used e.g. for scanned slides/negatives that never had EXIF).

    Reference timestamp on Windows: LastWriteTime, NOT CreationTime. Windows resets
    CreationTime to "now" whenever a file is copied (Explorer, robocopy, etc.), while
    LastWriteTime is normally preserved from the source file - so after any copy/sync,
    CreationTime can end up *later* than LastWriteTime, which is backwards from what the
    name suggests. LastWriteTime is the more trustworthy "when was this actually taken"
    proxy here, so it's what gets compared against the year folder and what "no metadata"
    corrections read the month/day from.

.PARAMETER RootDir
    Root directory containing year-named subfolders (e.g. "2020", "1998").

.EXAMPLE
    .\check_pic_dates.ps1 -RootDir "D:\Photos\Archive"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RootDir
)

$FileExtensions = @("jpg", "jpeg", "png", "heic", "mkv", "mp4", "mov", "avi")

function Write-Log {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
    Write-Host $line
    Add-Content -Path $script:LogFile -Value $line
}

# exiftool.exe is required for the metadata lookups below; fail early with a clear
# message instead of silently treating every file as "no metadata found".
if (-not (Get-Command exiftool -ErrorAction SilentlyContinue)) {
    Write-Error "exiftool(.exe) not found in PATH. Download from https://exiftool.org and add it to PATH."
    exit 1
}

if (-not (Test-Path -Path $RootDir -PathType Container)) {
    Write-Error "Directory not found: $RootDir"
    exit 1
}

$RootDir = (Resolve-Path $RootDir).Path
# Log lives with the archive being processed, same convention as the bash version.
$script:LogFile = Join-Path $RootDir "check_pic_dates.log"

$ProcessAll = $false

# Only top-level year folders (4-digit names) - anything else (e.g. "mixed", ".fullmix")
# is skipped entirely, same as the bash version.
$yearDirs = Get-ChildItem -Path $RootDir -Directory | Where-Object { $_.Name -match '^\d{4}$' } | Sort-Object Name

foreach ($yearDir in $yearDirs) {
    $yearFromDir = [int]$yearDir.Name
    Write-Host "Processing directory: $($yearDir.Name)"

    # Per-directory prompt: Yes / No (abort) / Skip this dir / All (stop asking).
    if (-not $ProcessAll) {
        $reply = Read-Host "Continue? (Y/N/S/A)"
    } else {
        $reply = "Y"
    }

    if ($reply -match '^[Aa]') {
        $ProcessAll = $true
        $reply = "Y"  # "All" implies processing this directory too
    }

    if ($reply -match '^[Nn]') {
        Write-Host "Aborting."
        exit 0
    }
    elseif ($reply -match '^[Ss]') {
        Write-Host "Skipping directory: $($yearDir.Name)"
        continue
    }
    elseif ($reply -notmatch '^[Yy]') {
        Write-Host "Invalid input. Aborting."
        exit 1
    }

    $files = Get-ChildItem -Path $yearDir.FullName -Recurse -File |
        Where-Object { $FileExtensions -contains $_.Extension.TrimStart('.').ToLower() }

    foreach ($file in $files) {
        try {
            # --- Filesystem timestamp reference: LastWriteTime, see header comment ---
            $fsDate = $file.LastWriteTime
            $yearFromFs = $fsDate.Year

            # --- Metadata extraction ---
            # Try image EXIF date first, then fall back to common video date tags.
            # This is the authoritative source when present - takes priority over both
            # the filesystem timestamp above and the year folder name.
            $metaRaw = & exiftool -s -s -s -DateTimeOriginal "$($file.FullName)" 2>$null
            if ([string]::IsNullOrWhiteSpace($metaRaw)) {
                $metaRaw = & exiftool -s -s -s -CreateDate "$($file.FullName)" 2>$null
            }
            if ([string]::IsNullOrWhiteSpace($metaRaw)) {
                $metaRaw = & exiftool -s -s -s -MediaCreateDate "$($file.FullName)" 2>$null
            }

            $metaDate = $null
            if (-not [string]::IsNullOrWhiteSpace($metaRaw) -and $metaRaw.Trim() -ne "0000:00:00 00:00:00") {
                # exiftool date format is "YYYY:MM:DD HH:MM:SS" - normalize the date part
                # so [datetime]::Parse can handle it.
                $normalized = $metaRaw.Trim() -replace '^(\d{4}):(\d{2}):(\d{2})', '$1-$2-$3'
                try {
                    $metaDate = [datetime]::Parse($normalized)
                } catch {
                    Write-Log "Could not parse metadata date '$metaRaw' for file $($file.FullName). Skipping metadata checks."
                }
            }

            if ($metaDate) {
                $yearFromMeta = $metaDate.Year

                # 5.a - filesystem date disagrees with EXIF: re-stamp file to the real
                # capture date so picframe/Explorer sort correctly.
                if ($yearFromFs -ne $yearFromMeta) {
                    Write-Log "Updating file date for $($file.FullName) to metadata date $metaDate"
                    $file.CreationTime = $metaDate
                    $file.LastWriteTime = $metaDate
                }

                # 5.b - EXIF year disagrees with the folder it's filed under: offer to
                # move it into the correct year folder (interactive, per file).
                if ($yearFromMeta -ne $yearFromDir) {
                    $moveReply = Read-Host "Move $($file.FullName) to $RootDir\$yearFromMeta ? (Y/N)"
                    if ($moveReply -match '^[Yy]') {
                        $relativeSubdir = $file.DirectoryName.Substring($yearDir.FullName.Length).TrimStart('\')
                        $newDir = Join-Path (Join-Path $RootDir "$yearFromMeta") $relativeSubdir
                        New-Item -ItemType Directory -Path $newDir -Force | Out-Null
                        Move-Item -Path $file.FullName -Destination $newDir
                        Write-Log "Moved $($file.FullName) to $newDir"
                    }
                }
                continue
            }

            # 6.a - No usable metadata at all: trust the manual year-folder sorting
            # instead. Keeps the original month/day/time (from LastWriteTime), only
            # corrects the year to match the folder.
            if ($yearFromFs -ne $yearFromDir) {
                Write-Log "No metadata found. Updating file year for $($file.FullName) to $yearFromDir"
                $corrected = Get-Date -Year $yearFromDir -Month $fsDate.Month -Day $fsDate.Day `
                    -Hour $fsDate.Hour -Minute $fsDate.Minute -Second $fsDate.Second
                $file.CreationTime = $corrected
                $file.LastWriteTime = $corrected
            }
        }
        catch {
            Write-Log "ERROR processing $($file.FullName): $_"
        }
    }
}
