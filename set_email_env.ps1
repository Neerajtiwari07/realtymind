param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("gmail", "sendgrid")]
    [string]$Provider,

    [Parameter(Mandatory = $true)]
    [string]$FromEmail,

    [Parameter(Mandatory = $true)]
    [string]$Username,

    [Parameter(Mandatory = $true)]
    [string]$Password
)

$env:EMAIL_PROVIDER = $Provider
$env:DEFAULT_FROM_EMAIL = $FromEmail
$env:EMAIL_HOST_USER = $Username
$env:EMAIL_HOST_PASSWORD = $Password
$env:EMAIL_PORT = "587"

if ($Provider -eq "sendgrid") {
    $env:EMAIL_HOST = "smtp.sendgrid.net"
}

Write-Output "Email environment variables set for provider: $Provider"
Write-Output "Now run: python manage.py runserver"
