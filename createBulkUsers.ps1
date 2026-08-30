$baseUrl = "https://archer-irm.com/archer"

$loginUrl = "$baseUrl/platformapi/core/security/login"
$loginBody = @{
    InstanceName = "t202603"
    Username     = "trainer"
    UserDomain   = ""
    Password     = "Archer@123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod `
        -Uri $loginUrl `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody
} catch {
    Write-Error "Failed to log in to Archer: $($_.Exception.Message)"
    exit 1
}

$sessionToken = $loginResponse.RequestedObject.SessionToken
if (-not $sessionToken) {
    Write-Error "Archer login did not return a session token."
    exit 1
}

$users = Import-Csv -Path (Join-Path $PSScriptRoot "users.csv")
$createUserUrl = "$baseUrl/platformapi/core/system/user"
$headers = @{
    Authorization = "Archer session-id=$sessionToken"
}

foreach ($user in $users) {
    $createUserBody = @{
        User = @{
            UserName  = $user.Username
            FirstName = $user.FirstName
            LastName  = $user.LastName
        }
        Password = $user.Password
    } | ConvertTo-Json -Depth 3

    try {
        $createResponse = Invoke-RestMethod `
            -Uri $createUserUrl `
            -Method Post `
            -Headers $headers `
            -ContentType "application/json" `
            -Body $createUserBody
    } catch {
        Write-Host "Failed to create user: $($user.Username) Response: $($_.Exception.Message)"
        continue
    }

    if (-not $createResponse.IsSuccessful) {
        Write-Host "Failed to create user: $($user.Username) Response: $($createResponse | ConvertTo-Json -Depth 10 -Compress)"
        continue
    }

    Write-Host "Successfully created user: $($user.Username) Response: $($createResponse | ConvertTo-Json -Depth 10 -Compress)"
    $userId = [int]$createResponse.RequestedObject.Id

    foreach ($group in ($user.Group -split "/")) {
        $addUserToGroupUrl = "$baseUrl/platformapi/core/system/usergroup"
        $addUserToGroupBody = @{
            UserId  = $userId
            GroupId = [int]$group
            IsAdd   = $true
        } | ConvertTo-Json

        try {
            $groupResponse = Invoke-RestMethod `
                -Uri $addUserToGroupUrl `
                -Method Put `
                -Headers $headers `
                -ContentType "application/json" `
                -Body $addUserToGroupBody
        } catch {
            Write-Host "Failed to add user: $($user.Username) to group: $group Response: $($_.Exception.Message)"
            continue
        }

        if ($groupResponse.IsSuccessful) {
            Write-Host "Successfully added user: $($user.Username) to group: $group"
        } else {
            Write-Host "Failed to add user: $($user.Username) to group: $group Response: $($groupResponse | ConvertTo-Json -Depth 10 -Compress)"
        }
    }
}