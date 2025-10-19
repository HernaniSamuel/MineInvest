/*
 * Copyright 2025 Hernani Samuel Diniz
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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