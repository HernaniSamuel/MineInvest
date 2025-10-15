import { Card, Row, Col } from 'react-bootstrap';

function StatCard({ icon, iconBg, label, value, meta, actions, valueClass = '' }) {
    return (
        <div className="stat-card-large d-flex gap-3 align-items-start">
            <div
                className={`stat-icon bg-${iconBg}`}
                style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    flexShrink: 0,
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
                }}
            >
                <i className={`bi bi-${icon}`}></i>
            </div>
            <div className="flex-grow-1">
                <small className="text-muted d-block mb-1" style={{
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    fontWeight: 600
                }}>
                    {label}
                </small>
                <div
                    className={`fw-bold font-monospace mb-1 ${valueClass}`}
                    style={{
                        fontSize: '1.5rem',
                        lineHeight: 1.2
                    }}
                >
                    {value}
                </div>
                {meta && (
                    <small className="text-muted" style={{ fontSize: '0.875rem' }}>
                        {meta}
                    </small>
                )}
                {actions && (
                    <div className="mt-2">
                        {actions}
                    </div>
                )}
            </div>
        </div>
    );
}

export default StatCard;