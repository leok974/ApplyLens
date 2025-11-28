param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
docker run --rm -v "${PWD}:/work" zricethezav/gitleaks:v8.18.4 detect --source /work @Args
