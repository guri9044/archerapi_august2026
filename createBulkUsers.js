const fs = require("node:fs");
const path = require("node:path");
const { parse } = require("csv-parse/sync");

const baseUrl = "https://archer-irm.com/archer";

async function sendJson(url, method, body, headers = {}) {
    const response = await fetch(url, {
        method,
        headers: {
            "Content-Type": "application/json",
            ...headers,
        },
        body: JSON.stringify(body),
    });

    const responseText = await response.text();
    let responseBody = null;

    try {
        responseBody = JSON.parse(responseText);
    } catch {
        // Preserve the raw response for non-JSON API errors.
    }

    return { response, responseBody, responseText };
}

async function main() {
    const loginUrl = `${baseUrl}/platformapi/core/security/login`;
    const loginBody = {
        InstanceName: "t202603",
        Username: "trainer",
        UserDomain: "",
        Password: "Archer@123",
    };

    const loginResult = await sendJson(loginUrl, "POST", loginBody);
    if (!loginResult.response.ok) {
        throw new Error(
            `Failed to log in to Archer: ${loginResult.response.status} ${loginResult.responseText}`,
        );
    }

    const sessionToken = loginResult.responseBody?.RequestedObject?.SessionToken;
    if (!sessionToken) {
        throw new Error("Archer login did not return a session token.");
    }

    const csvPath = path.join(__dirname, "users.csv");
    const users = parse(fs.readFileSync(csvPath, "utf8"), {
        bom: true,
        columns: true,
        skip_empty_lines: true,
        trim: true,
    });

    const createUserUrl = `${baseUrl}/platformapi/core/system/user`;
    const headers = {
        Authorization: `Archer session-id=${sessionToken}`,
    };

    for (const user of users) {
        const createUserBody = {
            User: {
                UserName: user.Username,
                FirstName: user.FirstName,
                LastName: user.LastName,
            },
            Password: user.Password,
        };

        const createResult = await sendJson(
            createUserUrl,
            "POST",
            createUserBody,
            headers,
        );

        if (!createResult.response.ok) {
            console.error(
                `Failed to create user: ${user.Username} Response: ${createResult.response.status} ${createResult.responseText}`,
            );
            continue;
        }

        if (!createResult.responseBody?.IsSuccessful) {
            console.error(
                `Failed to create user: ${user.Username} Response: ${JSON.stringify(createResult.responseBody)}`,
            );
            continue;
        }

        console.log(
            `Successfully created user: ${user.Username} Response: ${JSON.stringify(createResult.responseBody)}`,
        );

        const userId = Number(createResult.responseBody.RequestedObject.Id);
        for (const group of user.Group.split("/")) {
            const addUserToGroupUrl = `${baseUrl}/platformapi/core/system/usergroup`;
            const addUserToGroupBody = {
                UserId: userId,
                GroupId: Number(group),
                IsAdd: true,
            };

            const groupResult = await sendJson(
                addUserToGroupUrl,
                "PUT",
                addUserToGroupBody,
                headers,
            );

            if (!groupResult.response.ok) {
                console.error(
                    `Failed to add user: ${user.Username} to group: ${group} Response: ${groupResult.response.status} ${groupResult.responseText}`,
                );
                continue;
            }

            if (groupResult.responseBody?.IsSuccessful) {
                console.log(
                    `Successfully added user: ${user.Username} to group: ${group}`,
                );
            } else {
                console.error(
                    `Failed to add user: ${user.Username} to group: ${group} Response: ${JSON.stringify(groupResult.responseBody)}`,
                );
            }
        }
    }
}

main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
});