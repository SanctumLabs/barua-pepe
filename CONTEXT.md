# Email Gateway

This context describes the messages the gateway accepts and the people or systems involved in sending them.

## Message

**Email Request**:
An instruction to send an email, consisting of a sender, recipients, subject, message, and optional copies or attachments.
_Avoid_: Email, delivery (when referring to the instruction rather than its outcome)

**Subject**:
The concise heading associated with an email request.
_Avoid_: Title

**Message**:
The text or HTML content of an email request.
_Avoid_: Body (when referring to the complete request)

**Attachment**:
A file included with an email request, represented by its content, filename, and media type.
_Avoid_: File (when referring to the included email content)

## Participants

**Sender**:
The email address and display name presented as the originator of an email request.
_Avoid_: From (outside the email's recipient-role notation)

**Recipient**:
A party identified by an email address and optional display name who is included in an email request.
_Avoid_: Contact

**To recipient**:
A primary recipient of an email request.
_Avoid_: Main recipient

**CC recipient**:
A recipient copied visibly on an email request.
_Avoid_: Copy recipient

**BCC recipient**:
A recipient copied without being shown to other recipients.
_Avoid_: Hidden recipient

## Sending

**Email provider**:
A system to which the gateway submits a delivery attempt, such as an SMTP server or a third-party mail provider.
_Avoid_: Mail service (when referring to the external sender)

**Dispatch**:
Acceptance of an email request for asynchronous processing; dispatch does not establish that a provider accepted or delivered the email.
_Avoid_: Delivery, sent (when describing acceptance alone)

**Delivery attempt**:
An effort to submit an email request to an email provider.
_Avoid_: Dispatch

**Delivery failure**:
A delivery attempt that the provider explicitly rejects without accepting the email request.
_Avoid_: Failed dispatch

**Unknown delivery outcome**:
A delivery attempt for which the gateway cannot determine whether the provider accepted the email request.
_Avoid_: Delivery failure (unless rejection is confirmed)
