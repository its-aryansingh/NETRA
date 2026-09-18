// NETRA Cedar Remediation Policy
// Governs which remediation action may run on which AWS resource.
// Principle: forbid always wins over permit.

// 1. Forbid any mutating action on protected resources
@id("forbid_protected")
forbid (
    principal,
    action,
    resource
)
when {
    resource.is_protected == true
};

// 2. Forbid destructive actions when resource has active dependencies
@id("forbid_dependents")
forbid (
    principal,
    action in [
        Action::"terminate",
        Action::"delete",
        Action::"snapshot_and_terminate",
        Action::"snapshot_and_delete"
    ],
    resource
)
when {
    context.dependent_count > 0
};

// 3. Forbid bare destructive termination without a safeguarding snapshot
@id("forbid_unsnapshotted")
forbid (
    principal,
    action in [
        Action::"terminate",
        Action::"delete"
    ],
    resource
)
unless {
    context.has_snapshot_step == true
};

// 4. Permit authorized owners to execute non-destructive operational actions
@id("permit_owner")
permit (
    principal,
    action in [
        Action::"stop",
        Action::"downsize",
        Action::"none"
    ],
    resource
);

// 5. Permit destructive actions only when safeguarding snapshot is verified
@id("permit_owner_destructive")
permit (
    principal,
    action in [
        Action::"terminate",
        Action::"delete",
        Action::"snapshot_and_terminate",
        Action::"snapshot_and_delete"
    ],
    resource
)
when {
    context.has_snapshot_step == true
};
