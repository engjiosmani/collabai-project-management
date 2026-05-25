function EmptyState({
    icon = ".",
    kicker,
    title,
    description,
    actionLabel,
    onAction,
    actionHref,
    actionClassName = "dashboard-button dashboard-button--primary",
    className = "",
    compact = false,
}) {
    const hasAction = actionLabel && (onAction || actionHref);
    const Component = actionHref ? "a" : "button";
    const showIconText = icon && (icon === "!" || icon.length > 1);

    return (
        <section
            className={`ui-empty-state${compact ? " ui-empty-state--compact" : ""} ${className}`.trim()}
        >
            <div className="ui-empty-state__icon" aria-hidden="true">
                {showIconText ? icon : <span className="ui-empty-state__mark" />}
            </div>
            <div className="ui-empty-state__body">
                {kicker ? <p className="dashboard-empty-kicker">{kicker}</p> : null}
                <h3>{title}</h3>
                {description ? <p>{description}</p> : null}
            </div>
            {hasAction ? (
                <Component
                    type={actionHref ? undefined : "button"}
                    href={actionHref}
                    className={actionClassName}
                    onClick={onAction}
                >
                    {actionLabel}
                </Component>
            ) : null}
        </section>
    );
}

export default EmptyState;

