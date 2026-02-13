# Secure Identity Setup (Cloudflare Access) 🛡️

To activate the **Role-Based Access Control** we just built into the server, you need to enable Cloudflare Access. This will replace the manual password with a secure Google/GitHub/Email login.

### 1. Enable Access for the Tunnel
1.  Go to the [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
2.  Navigate to **Access > Applications**.
3.  Click **Add an Application** and select **Self-hosted**.
4.  **Application Domain**: Enter the exact tunnel URL (e.g., `seeker-packaging-mesa-share.trycloudflare.com`).
5.  **Application Name**: `Gaza Shared Brain`.

### 2. Configure Policies
Add a policy called `Team Access`:
*   **Action**: Allow.
*   **Assign to group**: (Create a group or add emails directly).
*   **Include**: Emails of Trustees and yourself.

### 3. Verify Identity Headers
Once enabled, Cloudflare will automatically inject the following header into every request:
`Cf-Access-Authenticated-User-Email`

Our server (`onboarding_server.py`) is already configured to read this header. 
*   If the email matches `ADMIN_EMAIL` in your `.env`, the user gets **ADMIN** rights.
*   If the email is anything else (but verified by Cloudflare), they get **READER** rights.

### 4. Local Testing
If you are testing locally (without the tunnel), you can still use the password `admin123` at `/login` to simulate the Admin session.

---
*Configured for the Gaza Resilience Fund Infrastructure*
