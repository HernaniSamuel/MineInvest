import { Card, Row, Col } from 'react-bootstrap';

function StatCard({ icon, iconBg, label, value, meta, actions, valueClass = '' }) {
    return (
        <div className="stat-card-large d-flex gap-3 align-items-start">
            <div className={`stat-icon bg-${iconBg}`}>
                <i className={`bi bi-${icon}`}></i>
            </div>
            <div className="flex-grow-1">
                <small className="text-muted d-block mb-1" style={{ 
                    fontSize: '0.75rem', 
                    textTransform: 'uppercase', 
                    letterSpacing: '0.5px' 
                }}>
                    {label}
                </small>
                <div 
                    className={`fw-bold font-monospace mb-1 ${valueClass}`}
                    style={{ fontSize: '1.5rem' }}
                >
                    {value}
                </div>
                {meta && (
                    <small className="text-muted">{meta}</small>
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