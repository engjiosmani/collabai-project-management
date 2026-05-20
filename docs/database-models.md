#  Database Models – CollabAI

## Overview

This document describes the foundational database models implemented for the CollabAI backend.

The models follow:

* Object-Oriented Programming (OOP)
* Django ORM best practices
* Multi-tenancy architecture
* Role-Based Access Control (RBAC)

---

## Core Models

### BaseModel (Abstract)

All models inherit from `BaseModel`, which provides:

* `created_at`
* `updated_at`

---

### Organization

Represents a company (tenant).

* One Organization → Many Workspaces

---

### Workspace

Represents a working environment inside an organization.

* Belongs to Organization
* Has multiple Roles
* Used for multi-tenancy

---

### Role

Defines user roles inside a workspace.

* Belongs to Workspace
* Has many Permissions (Many-to-Many)

---

### Permission

Defines allowed actions.

Examples:

* `create_task`
* `update_project`
* `delete_user`

---

### Profile

Extends the default Django User.

* One-to-one with User
* Can belong to Workspace
* Can have a Role

---

## 🔗 Model Relationships

Organization
└── Workspace
  ├── Role
  │  └── Permissions (M2M)
  └── Profile
    └── User (1-1)

---

##  Design Decisions

### OOP

* Shared fields handled via `BaseModel`

### Multi-Tenancy

* Implemented via Organization → Workspace hierarchy

### RBAC

* Implemented via Role + Permission

---

##  Testing

* Model creation tested
* Relationships verified
* All tests pass successfully

---

##  Migration Status

* Initial migrations created
* Applied successfully
* No system errors detected


---

# DB-02 Production Models

## Overview

The database architecture was expanded to support a production-ready project management system.

Additional production models were introduced to support:
- Project management
- Task management
- Team collaboration
- Notifications
- AI integration
- Audit logging
- Workspace memberships
- Integrations and subscriptions

---

## Production Models

### Projects
- Project
- ProjectMember
- Subscription
- Integration

### Tasks
- Task
- TaskStatus
- TaskPriority
- Label
- TaskLabel
- Attachment

### Collaboration
- Comment
- ActivityLog
- Notification

### AI Features
- AIRequest
- CacheEntity

### Workspace Management
- TeamMember
- OrganizationInvite

### Audit System
- AuditLog

---

## Database Features

### Indexes

Indexes were added for:
- Project filtering
- Task queries
- Notifications
- Activity logs
- Audit logs

### Constraints

Unique constraints implemented for:
- Workspace project names
- Team memberships
- Task labels
- Organization invites
- Integrations

---

## Extended Relationships

Workspace
├── Projects
│   ├── Tasks
│   │   ├── Comments
│   │   ├── Attachments
│   │   ├── ActivityLogs
│   │   └── Labels
│   ├── Members
│   └── Integrations
├── TeamMembers
├── OrganizationInvites
└── Subscription

User
├── Notifications
├── AIRequests
├── Comments
└── AuditLogs

---

## Architecture Notes

- All models inherit from `BaseModel`
- Django ORM relationships are normalized
- Multi-tenancy is implemented through Workspace architecture
- RBAC is implemented through Role and Permission
- Database indexing improves query performance
- Constraints enforce data integrity

---

## Testing & Migration Status

- All migrations generated successfully
- Migrations apply cleanly
- System checks pass without errors
- Unit tests verify relationships and constraints
- Django admin integration completed
