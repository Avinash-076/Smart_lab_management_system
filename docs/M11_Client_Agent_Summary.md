# M-11 Remote Command Management --- Client Agent Summary

## 1. Purpose

The Client Agent is responsible for receiving remote control commands
from the trusted Host, verifying that the command is authentic and
authorized, safely executing the approved operation, and returning the
result to the Host.

The core flow is:

``` text
Host
  ↓
WebSocket / WSS
  ↓
Client Agent
  ↓
Message validation
  ↓
Host signature verification
  ↓
Timestamp validation
  ↓
Nonce / replay protection
  ↓
Command whitelist / authorization
  ↓
Command execution
  ↓
Result
  ↓
WebSocket / WSS
  ↓
Host
```

## 2. Host and Client Key Design

The Host generates an asymmetric key pair:

``` text
Host
 ├── Private Key  → kept secret on Host
 └── Public Key   → provisioned to Client
```

### Private Key

The Host's private key is never sent to the Client. It is used by the
Host to digitally sign commands.

### Public Key

The Client stores the trusted Host public key during initial setup. It
uses this public key to verify signatures created by the Host's private
key.

The public key normally does **not** need to be sent with every command.

``` text
Initial setup:
Host Public Key → Client stores/trusts it

Normal operation:
Host Private Key → signs command
Signed command → Client
Client Public Key → verifies signature
```

The Client does not directly inspect or receive the private key. It
verifies that the received signature corresponds to the trusted Host
public key.

## 3. Command Authentication

A command should contain fields such as:

``` json
{
  "type": "command",
  "command_id": "CMD-1001",
  "command": "RESTART",
  "timestamp": 1786545000,
  "nonce": "unique-random-value",
  "signature": "digital-signature"
}
```

The Host signs the important command fields using its private key.

The Client verifies the signature using its pre-trusted Host public key.

If the signature is invalid, the command is rejected.

This prevents another device from simply sending a command such as
`RESTART` and having the Client execute it.

## 4. Timestamp Validation

The Client checks the command timestamp.

The purpose is to reject commands that are too old.

For example:

``` text
Current time
     ↓
Compare with command timestamp
     ↓
Within allowed time window?
   /         YES        NO
  ↓          ↓
Continue    Reject
```

A timestamp alone is not sufficient for authentication, but it helps
limit the lifetime of a captured command.

## 5. Nonce and Replay Protection

A nonce means "number used once."

The Client keeps track of recently used nonces.

``` text
First command:
Nonce = ABC123
       ↓
Not used before
       ↓
Accept

Repeated command:
Nonce = ABC123
       ↓
Already used
       ↓
Reject
```

The nonce prevents an attacker from replaying a previously valid
command.

The `command_id` identifies the request, while the nonce provides a
separate mechanism for detecting reuse.

## 6. Command Authorization and Whitelist

The Client must only execute predefined operations.

Example whitelist:

``` text
GET_STATUS
LOCK
RESTART
SHUTDOWN
```

If the Client receives an unsupported command:

``` text
FORMAT_DISK
DELETE_FILES
ARBITRARY_COMMAND
```

it must reject it.

The important security rule is:

> Never take arbitrary text received over WebSocket and pass it directly
> to a shell.

Instead, map each approved command to a specific implementation:

``` text
"GET_STATUS" → get system status
"LOCK"       → lock workstation
"RESTART"    → restart operation
"SHUTDOWN"   → shutdown operation
```

## 7. Command Processing Pipeline

The Client Agent processes commands in this order:

``` text
1. Receive WebSocket message
        ↓
2. Parse JSON
        ↓
3. Validate required fields
        ↓
4. Verify Host digital signature
        ↓
5. Validate timestamp
        ↓
6. Validate nonce / detect replay
        ↓
7. Check command whitelist
        ↓
8. Execute predefined operation
        ↓
9. Generate result
        ↓
10. Send result to Host
```

Execution should happen only after all relevant validation checks
succeed.

## 8. Command Results

After executing a command, the Client sends a result containing the
original command ID.

Example:

``` json
{
  "type": "command_result",
  "command_id": "CMD-1001",
  "client_id": "PC-05",
  "status": "SUCCESS",
  "timestamp": 1786545005,
  "result": {
    "message": "Restart scheduled"
  }
}
```

Possible statuses include:

``` text
SUCCESS
FAILED
UNAUTHORIZED
REJECTED
INVALID_MESSAGE
```

The `command_id` allows the Host to associate the result with the
original command.

## 9. WebSocket Role

WebSocket is the communication transport.

It provides the channel:

``` text
Host
  ↕
WebSocket
  ↕
Client Agent
```

WebSocket itself does **not** prove that a command came from the trusted
Host.

Authentication and authorization are provided by mechanisms such as:

-   TLS/WSS
-   Host public/private key signatures
-   Timestamp validation
-   Nonce/replay protection
-   Command whitelist
-   Authorization rules

For production, use:

``` text
wss://
```

instead of an unencrypted:

``` text
ws://
```

## 10. Client Agent Responsibilities

The Client Agent is responsible for:

-   Maintaining the WebSocket connection.
-   Receiving command messages.
-   Validating message structure.
-   Verifying the trusted Host's digital signature.
-   Checking command freshness.
-   Detecting replayed commands.
-   Checking the command whitelist.
-   Executing only predefined operations.
-   Returning execution results.
-   Handling connection failures and reconnecting.

## 11. Security Model

The security layers work together:

``` text
                Client Agent
                     │
                     ▼
             WSS / TLS
          Protects connection
                     │
                     ▼
          Host Signature Check
       Proves trusted Host signed it
                     │
                     ▼
          Timestamp Validation
          Limits command lifetime
                     │
                     ▼
             Nonce Validation
            Prevents replay
                     │
                     ▼
           Command Whitelist
          Limits allowed actions
                     │
                     ▼
              Execute
```

No single layer should be treated as the complete security mechanism.

## 12. Key Provisioning

During initial setup:

``` text
Host generates:
    Private Key
    Public Key

Private Key:
    stays on Host

Public Key:
    securely provisioned to Client
```

During normal operation, the public key is reused for signature
verification.

If the Host private key is compromised, the system should support key
rotation:

``` text
Compromised Key
      ↓
Revoke old public key
      ↓
Generate new Host key pair
      ↓
Provision new public key
      ↓
Clients trust new key
```

## 13. Final Design

The complete M-11 Client Agent design is:

``` text
                         HOST
                           │
                  Create command
                           │
                  Sign with private key
                           │
                           ▼
                    WebSocket / WSS
                           │
                           ▼
                    CLIENT AGENT
                           │
                           ▼
                  Validate message
                           │
                           ▼
                Verify Host signature
                           │
                           ▼
                 Check timestamp
                           │
                           ▼
                 Check nonce/replay
                           │
                           ▼
                Check authorization
                           │
                           ▼
                 Check whitelist
                           │
                      ┌────┴────┐
                      │         │
                    Valid     Invalid
                      │         │
                      ▼         ▼
                   Execute    Reject
                      │
                      ▼
                 Generate result
                      │
                      ▼
                 WebSocket / WSS
                      │
                      ▼
                     HOST
```

## 14. Core Principle

The Client Agent should follow one fundamental rule:

> **Never execute a remote command just because it arrived through
> WebSocket.**

The command must first be authenticated, validated, authorized, and
matched against the allowed command set. Only then should the Client
execute the predefined operation and return the result.
