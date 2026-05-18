# Planora Admin Dashboard Frontend Memo

Last updated: 2026-05-18

This memo records the latest admin-dashboard frontend fixes discussed and implemented locally during the dashboard UI polish session. It is saved in the backend repository because this GitHub connector currently has access to `ibrahimoll/planora-backend`; the Next.js admin-dashboard frontend files were provided through pasted code/local screenshots rather than directly accessible from GitHub in this session.

## Current frontend work area

Local project path used by the user:

```txt
C:\Users\mahdi\OneDrive\Documents\Planora\admin-dashboard
```

Important frontend files involved:

```txt
admin-dashboard/components/PlanoraLogo.tsx
admin-dashboard/components/layout/AdminSidebar.tsx
admin-dashboard/components/layout/AdminTopbar.tsx
admin-dashboard/components/layout/ProtectedAdminLayout.tsx
admin-dashboard/app/dashboard/settings/page.tsx
admin-dashboard/lib/adminProfileSync.ts
admin-dashboard/lib/auth.ts
```

## Logo and sidebar state

The old green shield logo in the sidebar was removed.

Current sidebar logo direction:

- Use `components/PlanoraLogo.tsx`.
- Logo is an inline SVG/component, not a PNG file.
- Visual direction: dark SaaS/admin style, teal/cyan Planora mark, not a security shield.
- `AdminSidebar.tsx` must keep a named export because `ProtectedAdminLayout.tsx` imports it as:

```tsx
import { AdminSidebar } from "@/components/layout/AdminSidebar";
```

So the sidebar must be:

```tsx
export function AdminSidebar() {
  // ...
}
```

Do not change it to a default export unless all imports are updated.

## AdminTopbar fixes

`components/layout/AdminTopbar.tsx` was expanded to support real UI behavior instead of placeholder buttons.

Completed behavior:

- Search input works for dashboard sections.
- Search results dropdown opens on focus/type.
- Pressing Enter navigates to the first result.
- Search dropdown closes when clicking outside or pressing Escape.
- Notifications bell opens a dropdown.
- Notifications dropdown closes when clicking outside or pressing Escape.
- Profile dropdown closes when clicking outside or pressing Escape.
- Settings gear in the topbar was replaced with an admin profile avatar/dropdown.
- Topbar avatar reads from the same admin profile data as settings.
- Profile dropdown includes Admin profile and Logout.
- The protected badge remains as a small status badge.

## Profile image synchronization

Problem fixed:

- The settings page could update the admin full name or preview image, but the topbar did not update immediately because it had its own state.

Current solution:

- Shared helper file: `lib/adminProfileSync.ts`.
- Shared localStorage key: `current_admin`.
- Shared browser event: `planora-admin-profile-updated`.
- Settings page calls `saveAdminProfile(updatedUser)` after loading/saving/uploading/removing profile image.
- Topbar listens for `planora-admin-profile-updated` and updates its local state immediately.
- Topbar also refreshes `/auth/me` on mount/focus/visibility change where possible.

Important helper API in `lib/adminProfileSync.ts`:

```ts
export type AdminUser = {
  user_id?: number;
  username?: string;
  email?: string;
  full_name?: string;
  role?: string;
  profile_pic?: string | null;
  created_at?: string;
  is_active?: boolean;
  is_email_verified?: boolean;
};

export const ADMIN_PROFILE_STORAGE_KEY = "current_admin";
export const ADMIN_PROFILE_UPDATED_EVENT = "planora-admin-profile-updated";

export function saveAdminProfile(adminUser: AdminUser) {
  // saves current_admin and dispatches planora-admin-profile-updated
}
```

Settings page should call `saveAdminProfile(updatedProfile)` inside/after:

- initial `loadProfile()` success
- `handleSaveProfile()` success
- `handleProfilePictureChange()` success
- `handleRemoveProfilePicture()` success

## Initials consistency

Problem fixed:

- Settings profile card and topbar used different initials logic.
- Example: one showed only first letter, the other showed two letters.

Current rule everywhere:

```txt
Planora Ibrahim -> PI
Planora -> PL
Admin -> AD
```

The shared helper should be:

```ts
export function getAdminInitials(adminUser: AdminUser | null) {
  const source = getAdminDisplayName(adminUser).trim();

  if (!source) return "AD";

  const parts = source.split(" ").filter(Boolean);

  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }

  return source.slice(0, 2).toUpperCase() || "AD";
}
```

Settings page should either use this shared helper directly or use identical logic.

## Notification read-state persistence

Problem fixed:

- Pressing `Mark all read` worked visually, but refreshing the page reset the hardcoded notifications back to unread.

Current local frontend solution:

- `AdminTopbar.tsx` stores notification read/unread state in localStorage.
- localStorage key:

```txt
planora-admin-notifications
```

Expected behavior:

- Pressing `Mark all read` sets all notifications to `unread: false`.
- The state is persisted to localStorage.
- After refresh, notifications stay read.
- Clicking an individual notification can mark only that one as read.
- The unread dot on the bell depends on unread count.
- `Mark all read` should be disabled when unread count is zero.

Important type/constant pattern:

```ts
type AdminNotification = {
  id: number;
  title: string;
  message: string;
  time: string;
  unread: boolean;
};

const ADMIN_NOTIFICATIONS_STORAGE_KEY = "planora-admin-notifications";
```

Future backend replacement:

- The localStorage solution is acceptable for frontend-only placeholder notifications.
- When real backend notifications are wired, replace localStorage persistence with real API calls, for example:

```txt
GET /notifications
PATCH /notifications/{notification_id}/read
PATCH /notifications/mark-all-read
```

or admin-specific notification endpoints if the backend uses separate admin notification APIs.

## Logout fix

Problem fixed:

- Topbar logout did not reliably log out because only some localStorage keys were removed and protected layout state could remain active.

Current logout direction:

- Import and call `clearAdminToken()` from `@/lib/auth`.
- Remove common localStorage keys.
- Remove common sessionStorage keys.
- Clear common auth cookies defensively.
- Use `window.location.replace("/login")` instead of only `router.push("/login")` so the protected dashboard state fully resets.

Recommended logout cleanup keys:

```txt
admin_token
access_token
token
planora_token
planora_admin_token
current_admin
admin_user
current_user
user
planora_user
```

Important: The actual token key used by the admin dashboard login flow is `planora_admin_token`.

## Current admin-dashboard auth rule

- Admin dashboard login still uses the existing backend normal login endpoint.
- There is no separate admin login endpoint.
- Frontend must call `/auth/me` after login and require `role = admin`.
- Non-admins must be blocked and token cleared.
- Protected dashboard route must redirect to `/login` after token removal.

## Notes for future work

- Push the admin-dashboard frontend repository/code to GitHub so future reviews can inspect actual files directly instead of relying on screenshots and pasted code.
- Replace placeholder topbar notifications with real backend notification data when the admin notification API/UI is ready.
- Keep `docs/PLANORA_CONTEXT.md` as the main project context file.
- This file is a focused memo for the recent admin-dashboard frontend fixes only.
