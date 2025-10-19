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

import { useState } from 'react';
import { Modal, Button, Form, InputGroup, Alert } from 'react-bootstrap';
import { balanceAPI } from '../services/api';
import { formatCurrency } from '../utils/formatters';
import { showToast } from '../utils/toast';

function BalanceModal({ show, onHide, simulation, action, onSuccess }) {
    const [amount, setAmount] = useState('');
    const [removeInflation, setRemoveInflation] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const isAdding = action === 'add';
    const operation = isAdding ? 'ADD' : 'REMOVE';
    const category = isAdding ? 'contribution' : 'withdrawal';
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        
        setError(null);
        
        const parsedAmount = parseFloat(amount);
        
        if (!parsedAmount || parsedAmount <= 0) {
            showToast.warning('Please enter a valid amount');
            return;
        }
        
        setLoading(true);
        
        // Show loading toast
        const toastId = showToast.loading(
            `${isAdding ? 'Adding' : 'Removing'} ${formatCurrency(parsedAmount, simulation.base_currency)}...`
        );
        
        try {
            const response = await balanceAPI.modify(simulation.id, {
                amount: parsedAmount,
                operation: operation,
                category: category,
                remove_inflation: removeInflation
            });
            
            // Update loading toast to success
            showToast.update(
                toastId, 
                'success',
                `${isAdding ? 'Added' : 'Removed'} ${formatCurrency(parsedAmount, simulation.base_currency)}${removeInflation ? ' (inflation adjusted)' : ''}`
            );
            
            // Success! Call parent callback
            onSuccess(response.data);
            
            // Reset and close
            setAmount('');
            setRemoveInflation(false);
            setError(null);
            onHide();
            
        } catch (err) {
            console.error('❌ Balance operation failed:', err);
            showToast.update(
                toastId,
                'error',
                err.response?.data?.detail || 'Operation failed'
            );
            setError(err.response?.data?.detail || err.message || 'Operation failed');
        } finally {
            setLoading(false);
        }
    };
    
    const handleModalHide = () => {
        setAmount('');
        setRemoveInflation(false);
        setError(null);
        onHide();
    };
    
    const currencySymbol = simulation?.base_currency === 'BRL' ? 'R$' :
                          simulation?.base_currency === 'USD' ? '$' : '€';

    return (
        <Modal show={show} onHide={handleModalHide} centered>
            <Modal.Header closeButton className="bg-dark text-light border-secondary">
                <Modal.Title>
                    <i className={`bi bi-${isAdding ? 'plus' : 'dash'}-circle me-2`}></i>
                    {isAdding ? 'Add Money' : 'Remove Money'}
                </Modal.Title>
            </Modal.Header>
            
            <Form onSubmit={handleSubmit}>
                <Modal.Body className="bg-dark text-light">
                    {error && (
                        <Alert variant="danger" className="mb-3">
                            <i className="bi bi-exclamation-triangle me-2"></i>
                            {error}
                        </Alert>
                    )}
                    
                    <Form.Group className="mb-3">
                        <Form.Label>Amount</Form.Label>
                        <InputGroup size="lg">
                            <InputGroup.Text>{currencySymbol}</InputGroup.Text>
                            <Form.Control
                                type="number"
                                step="0.01"
                                min="0.01"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder="1000.00"
                                autoFocus
                                required
                                disabled={loading}
                            />
                        </InputGroup>
                        <Form.Text className="text-muted">
                            Enter the amount you want to {isAdding ? 'add' : 'remove'}
                        </Form.Text>
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                        <Form.Check
                            type="switch"
                            id="removeInflationSwitch"
                            label={
                                <>
                                    <i className="bi bi-percent me-1"></i>
                                    Remove accumulated IPCA inflation
                                </>
                            }
                            checked={removeInflation}
                            onChange={(e) => setRemoveInflation(e.target.checked)}
                            disabled={loading}
                        />
                        <Form.Text className="text-muted d-block mt-1">
                            Adjusts value for inflation since simulation start date
                        </Form.Text>
                    </Form.Group>
                    
                    <Alert variant="info" className="mb-0">
                        <i className="bi bi-info-circle me-2"></i>
                        <strong>Note:</strong> This operation will be recorded as a{' '}
                        <strong>{category}</strong> in your transaction history.
                    </Alert>
                </Modal.Body>
                
                <Modal.Footer className="bg-dark border-secondary">
                    <Button 
                        variant="secondary" 
                        onClick={handleModalHide}
                        disabled={loading}
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        variant={isAdding ? 'success' : 'danger'}
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                Processing...
                            </>
                        ) : (
                            <>
                                <i className="bi bi-check-circle me-2"></i>
                                {isAdding ? 'Add Money' : 'Remove Money'}
                            </>
                        )}
                    </Button>

                </Modal.Footer>
            </Form>
        </Modal>
    );
}

export default BalanceModal;