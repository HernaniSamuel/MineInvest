// Simulation View Screen

const SimulationViewScreen = {
    
    simulation: null,
    holdings: [],
    history: [],
    portfolioChart: null,
    allocationChart: null,
    
    // Initialize screen
    async init() {
        console.log('Initializing Simulation View Screen...');
        
        this.simulation = State.getCurrentSimulation();
        
        if (!this.simulation) {
            Utils.showToast('No simulation loaded', 'error');
            App.showScreen('simulationList');
            return;
        }
        
        this.setupEventListeners();
        await this.loadAllData();
    },
    
    // Setup event listeners
    setupEventListeners() {
        // Balance modal
        const balanceModal = document.getElementById('balanceModal');
        balanceModal.addEventListener('show.bs.modal', (e) => {
            const button = e.relatedTarget;
            const action = button.getAttribute('data-action');
            this.prepareBalanceModal(action);
        });
        
        // Prevent form submission (FIXED)
        document.getElementById('balanceForm').addEventListener('submit', (e) => {
            e.preventDefault();
        });
        
        document.getElementById('confirmBalanceBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.handleBalanceOperation();
        });
        
        // Advance month
        document.getElementById('advanceMonthBtn').addEventListener('click', () => {
            this.advanceMonth();
        });
        
        // Undo month
        document.getElementById('undoMonthBtn').addEventListener('click', () => {
            this.undoMonth();
        });
        
        // Go to trading
        document.getElementById('goToTradingBtn').addEventListener('click', () => {
            App.showScreen('trading');
        });
        
        // Refresh buttons
        document.getElementById('refreshChartsBtn').addEventListener('click', () => {
            this.loadAllData();
        });
        
        document.getElementById('refreshHoldingsBtn').addEventListener('click', () => {
            this.refreshHoldings();
        });
        
        // Toggle history
        document.getElementById('toggleHistoryBtn').addEventListener('click', () => {
            this.toggleHistory();
        });
    },
    
    // Load all data
    async loadAllData() {
        try {
            Utils.showLoading();
            
            await this.loadSimulation();
            await this.loadPortfolio();
            await this.loadHistory();
            
            this.updateUI();
            this.renderCharts();
            
            Utils.hideLoading();
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Failed to load data: ' + error.message, 'error');
        }
    },
    
    // Load simulation
    async loadSimulation() {
        this.simulation = await API.simulations.get(this.simulation.id);
        State.setCurrentSimulation(this.simulation);
    },
    
    // Load portfolio
    async loadPortfolio() {
        try {
            this.portfolio = await API.portfolio.get(this.simulation.id);
            this.holdings = this.portfolio.holdings || [];
        } catch (error) {
            console.error('Portfolio load error:', error);
            this.portfolio = {
                holdings: [],
                summary: {
                    total_holdings: 0,
                    total_market_value: "0.00",
                    total_invested: "0.00",
                    total_gain_loss: "0.00",
                    gain_loss_percentage: "0.00"
                }
            };
            this.holdings = [];
        }
    },
    
    // Load history
    async loadHistory() {
        try {
            this.history = await API.history.get(this.simulation.id);
        } catch (error) {
            console.error('History load error:', error);
            this.history = { months: [] };
        }
    },
    
    // Update UI elements
    updateUI() {
        const sim = this.simulation;
        const summary = this.portfolio.summary;
        
        // Title
        document.getElementById('simTitle').textContent = sim.name;
        document.getElementById('simSubtitle').textContent = 
            `${sim.base_currency} • Started ${Utils.formatDate(sim.start_date)} • Current: ${Utils.formatDate(sim.current_date)}`;
        
        // Balance
        const balance = parseFloat(sim.balance);
        document.getElementById('simCashBalance').textContent = 
            Utils.formatCurrency(balance, sim.base_currency);
        
        // Portfolio value
        const portfolioValue = parseFloat(summary.total_market_value);
        document.getElementById('simPortfolioValue').textContent = 
            Utils.formatCurrency(portfolioValue, sim.base_currency);
        document.getElementById('simHoldingsCount').textContent = 
            `${summary.total_holdings} holding${summary.total_holdings !== 1 ? 's' : ''}`;
        
        // Total value
        const totalValue = balance + portfolioValue;
        document.getElementById('simTotalValue').textContent = 
            Utils.formatCurrency(totalValue, sim.base_currency);
        
        // Gain/Loss
        const gainLoss = parseFloat(summary.total_gain_loss);
        const gainLossPercent = parseFloat(summary.gain_loss_percentage);
        
        const gainLossEl = document.getElementById('simGainLoss');
        const gainLossPercentEl = document.getElementById('simGainLossPercent');
        const gainLossIcon = document.getElementById('simGainLossIcon');
        
        gainLossEl.textContent = Utils.formatCurrency(gainLoss, sim.base_currency);
        gainLossPercentEl.textContent = Utils.formatPercent(gainLossPercent);
        
        // Color coding
        if (gainLoss >= 0) {
            gainLossEl.classList.add('gain');
            gainLossEl.classList.remove('loss');
            gainLossPercentEl.classList.add('gain');
            gainLossPercentEl.classList.remove('loss');
            gainLossIcon.className = 'stat-icon bg-success';
            gainLossIcon.innerHTML = '<i class="bi bi-arrow-up"></i>';
        } else {
            gainLossEl.classList.add('loss');
            gainLossEl.classList.remove('gain');
            gainLossPercentEl.classList.add('loss');
            gainLossPercentEl.classList.remove('gain');
            gainLossIcon.className = 'stat-icon bg-danger';
            gainLossIcon.innerHTML = '<i class="bi bi-arrow-down"></i>';
        }
        
        // Holdings table
        this.renderHoldingsTable();
        
        // Check if can advance month
        this.checkCanAdvance();
        
        // Check if can undo
        this.checkCanUndo();
    },
    
    // Render holdings table
    renderHoldingsTable() {
        const tbody = document.getElementById('holdingsTableBody');
        
        if (this.holdings.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center text-muted py-4">
                        <i class="bi bi-inbox display-4 mb-2 d-block"></i>
                        No holdings yet. Click "Trade Assets" to start investing!
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = '';
        
        this.holdings.forEach(holding => {
            const quantity = parseFloat(holding.quantity);
            const purchasePrice = parseFloat(holding.purchase_price);
            const currentPrice = parseFloat(holding.current_price);
            const marketValue = parseFloat(holding.market_value);
            const weight = parseFloat(holding.weight);
            
            const invested = quantity * purchasePrice;
            const gainLoss = marketValue - invested;
            const gainLossPercent = (gainLoss / invested) * 100;
            
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="fw-bold">${holding.ticker}</td>
                <td>${holding.name}</td>
                <td class="text-end font-monospace">${quantity.toFixed(4)}</td>
                <td class="text-end font-monospace">${Utils.formatCurrency(purchasePrice, holding.base_currency)}</td>
                <td class="text-end font-monospace">${Utils.formatCurrency(currentPrice, holding.base_currency)}</td>
                <td class="text-end font-monospace fw-bold">${Utils.formatCurrency(marketValue, holding.base_currency)}</td>
                <td class="text-end font-monospace">${weight.toFixed(2)}%</td>
                <td class="text-end font-monospace ${gainLoss >= 0 ? 'gain' : 'loss'}">
                    ${Utils.formatCurrency(gainLoss, holding.base_currency)}
                    <br>
                    <small>(${Utils.formatPercent(gainLossPercent)})</small>
                </td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-success me-1" onclick="alert('Buy more - Navigate to trading screen')" title="Buy more">
                        <i class="bi bi-plus"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="alert('Sell - Navigate to trading screen')" title="Sell">
                        <i class="bi bi-dash"></i>
                    </button>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    },
    
    // Render charts
    renderCharts() {
        this.renderPortfolioChart();
        this.renderAllocationChart();
    },
    
    // Render portfolio evolution chart
    renderPortfolioChart() {
        const ctx = document.getElementById('portfolioEvolutionChart');
        
        if (this.portfolioChart) {
            this.portfolioChart.destroy();
        }
        
        const labels = [];
        const cashData = [];
        const portfolioData = [];
        const totalData = [];
        
        if (this.history.months && this.history.months.length > 0) {
            this.history.months.forEach(month => {
                labels.push(Utils.formatDate(month.month_date));
                const balance = parseFloat(month.total);
                cashData.push(balance);
                portfolioData.push(0);
                totalData.push(balance);
            });
        } else {
            labels.push(Utils.formatDate(this.simulation.current_date));
            cashData.push(parseFloat(this.simulation.balance));
            portfolioData.push(parseFloat(this.portfolio.summary.total_market_value));
            totalData.push(parseFloat(this.simulation.balance) + parseFloat(this.portfolio.summary.total_market_value));
        }
        
        this.portfolioChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Total Value',
                        data: totalData,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Portfolio',
                        data: portfolioData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Cash',
                        data: cashData,
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#d1d5db',
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#f9fafb',
                        bodyColor: '#d1d5db',
                        borderColor: '#374151',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#374151',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#9ca3af',
                            callback: function(value) {
                                return 'R$ ' + value.toLocaleString('pt-BR', {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                });
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#9ca3af'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    },
    
    // Render asset allocation pie chart
    renderAllocationChart() {
        const ctx = document.getElementById('assetAllocationChart');
        const noHoldingsMsg = document.getElementById('noHoldingsMessage');
        
        if (this.allocationChart) {
            this.allocationChart.destroy();
            this.allocationChart = null;
        }
        
        if (this.holdings.length === 0) {
            ctx.style.display = 'none';
            noHoldingsMsg.style.display = 'block';
            return;
        }
        
        ctx.style.display = 'block';
        noHoldingsMsg.style.display = 'none';
        
        const labels = this.holdings.map(h => h.ticker);
        const data = this.holdings.map(h => parseFloat(h.market_value));
        const backgroundColors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
        ];
        
        this.allocationChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors.slice(0, labels.length),
                    borderColor: '#1f2937',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#d1d5db',
                            padding: 15,
                            generateLabels: (chart) => {
                                const data = chart.data;
                                return data.labels.map((label, i) => {
                                    const value = data.datasets[0].data[i];
                                    const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                    const percent = ((value / total) * 100).toFixed(1);
                                    return {
                                        text: `${label} (${percent}%)`,
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        hidden: false,
                                        index: i
                                    };
                                });
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                        titleColor: '#f9fafb',
                        bodyColor: '#d1d5db',
                        borderColor: '#374151',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percent = ((value / total) * 100).toFixed(2);
                                return `${label}: R$ ${value.toFixed(2)} (${percent}%)`;
                            }
                        }
                    }
                },
                cutout: '65%'
            }
        });
    },
    
    // Prepare balance modal (UPDATED - NO CATEGORY SELECTION)
    prepareBalanceModal(action) {
        document.getElementById('balanceAction').value = action;
        
        const isAdding = action === 'add';
        const title = isAdding ? 'Add Money' : 'Remove Money';
        const actionText = isAdding ? 'add' : 'remove';
        const category = isAdding ? 'contribution' : 'withdrawal';
        const btnClass = isAdding ? 'btn-success' : 'btn-danger';
        const btnText = isAdding ? 'Add Money' : 'Remove Money';
        const icon = isAdding ? 'plus-circle' : 'dash-circle';
        
        document.getElementById('balanceModalTitle').innerHTML = 
            `<i class="bi bi-${icon} me-2"></i>${title}`;
        
        document.getElementById('actionText').textContent = actionText;
        document.getElementById('categoryDisplay').textContent = category;
        
        const confirmBtn = document.getElementById('confirmBalanceBtn');
        confirmBtn.className = `btn ${btnClass}`;
        confirmBtn.innerHTML = `<i class="bi bi-check-circle me-2"></i>${btnText}`;
        
        document.getElementById('balanceAmount').value = '';
        document.getElementById('removeInflation').checked = false;
        
        const currencySymbols = {
            'BRL': 'R$',
            'USD': '$',
            'EUR': '€'
        };
        document.getElementById('balanceCurrencySymbol').textContent = 
            currencySymbols[this.simulation.base_currency] || this.simulation.base_currency;
        
        setTimeout(() => {
            document.getElementById('balanceAmount').focus();
        }, 500);
    },
    
    // Handle balance operation (UPDATED - AUTO CATEGORY)
    async handleBalanceOperation() {
        const form = document.getElementById('balanceForm');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const amount = parseFloat(document.getElementById('balanceAmount').value);
        const action = document.getElementById('balanceAction').value;
        const removeInflation = document.getElementById('removeInflation').checked;
        
        const isAdding = action === 'add';
        const operation = isAdding ? 'ADD' : 'REMOVE';
        const category = isAdding ? 'contribution' : 'withdrawal';
        
        try {
            Utils.showLoading();
            
            await API.balance.modify(this.simulation.id, {
                amount: amount,
                operation: operation,
                category: category,
                remove_inflation: removeInflation
            });
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('balanceModal'));
            modal.hide();
            
            Utils.hideLoading();
            
            const actionWord = isAdding ? 'added' : 'removed';
            const actionPrep = isAdding ? 'to' : 'from';
            
            Utils.showToast(
                `Successfully ${actionWord} ${Utils.formatCurrency(amount, this.simulation.base_currency)} ${actionPrep} balance${removeInflation ? ' (inflation adjusted)' : ''}`,
                'success'
            );
            
            await this.loadAllData();
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Operation failed: ' + error.message, 'error');
        }
    },
    
    // Refresh holdings
    async refreshHoldings() {
        try {
            Utils.showLoading();
            
            await API.holdings.refresh(this.simulation.id);
            
            Utils.hideLoading();
            Utils.showToast('Holdings prices updated!', 'success');
            
            await this.loadPortfolio();
            this.updateUI();
            this.renderCharts();
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Failed to refresh: ' + error.message, 'error');
        }
    },
    
    // Check if can advance month
    async checkCanAdvance() {
        try {
            const result = await API.time.canAdvance(this.simulation.id);
            
            const btn = document.getElementById('advanceMonthBtn');
            btn.disabled = !result.can_advance;
            
            if (!result.can_advance && result.reason) {
                btn.title = result.reason;
            } else {
                btn.title = 'Advance to next month';
            }
            
        } catch (error) {
            console.error('Check advance error:', error);
            document.getElementById('advanceMonthBtn').disabled = true;
        }
    },
    
    // Check if can undo
    async checkCanUndo() {
        try {
            const snapshot = await API.snapshot.get(this.simulation.id);
            
            const btn = document.getElementById('undoMonthBtn');
            btn.disabled = !snapshot.can_restore;
            
            if (snapshot.can_restore) {
                btn.title = `Restore to ${Utils.formatDate(snapshot.month_date)}`;
            } else {
                btn.title = 'No snapshot available for current month';
            }
            
        } catch (error) {
            console.error('Check undo error:', error);
            document.getElementById('undoMonthBtn').disabled = true;
        }
    },
    
    // Advance month
    async advanceMonth() {
        if (!confirm('Advance to next month? This will:\n\n• Process dividends\n• Update asset prices\n• Create a snapshot (for undo)\n\nContinue?')) {
            return;
        }
        
        try {
            Utils.showLoading();
            
            const report = await API.time.advance(this.simulation.id);
            
            Utils.hideLoading();
            
            this.showMonthAdvanceReport(report);
            
            await this.loadAllData();
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Failed to advance month: ' + error.message, 'error');
        }
    },
    
    // Show month advance report
    showMonthAdvanceReport(report) {
        const reportDiv = document.getElementById('monthAdvanceReport');
        
        let html = `
            <div class="mb-4">
                <h6 class="text-success"><i class="bi bi-calendar-check me-2"></i>Date Advanced</h6>
                <p class="mb-0">${Utils.formatDate(report.previous_date)} → ${Utils.formatDate(report.new_date)}</p>
            </div>
        `;
        
        if (report.dividends_received.length > 0) {
            html += `
                <div class="mb-4">
                    <h6 class="text-success"><i class="bi bi-coin me-2"></i>Dividends Received</h6>
                    <div class="table-responsive">
                        <table class="table table-dark table-sm">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th class="text-end">Per Share</th>
                                    <th class="text-end">Quantity</th>
                                    <th class="text-end">Total</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            report.dividends_received.forEach(div => {
                html += `
                    <tr>
                        <td>${div.ticker}</td>
                        <td class="text-end">${div.dividend_per_share}</td>
                        <td class="text-end">${div.quantity}</td>
                        <td class="text-end fw-bold text-success">${div.total}</td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                            <tfoot>
                                <tr class="table-active">
                                    <th colspan="3">Total Dividends</th>
                                    <th class="text-end">${report.total_dividends}</th>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="mb-4">
                    <h6 class="text-muted"><i class="bi bi-coin me-2"></i>No Dividends This Month</h6>
                </div>
            `;
        }
        
        if (report.price_updates.length > 0) {
            html += `
                <div class="mb-4">
                    <h6><i class="bi bi-graph-up me-2"></i>Price Updates</h6>
                    <div class="table-responsive">
                        <table class="table table-dark table-sm">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th class="text-end">Old Price</th>
                                    <th class="text-end">New Price</th>
                                    <th class="text-end">Change</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            
            report.price_updates.forEach(update => {
                const change = parseFloat(update.change);
                const changeClass = change >= 0 ? 'text-success' : 'text-danger';
                
                html += `
                    <tr>
                        <td>${update.ticker}</td>
                        <td class="text-end">${update.old_price}</td>
                        <td class="text-end fw-bold">${update.new_price}</td>
                        <td class="text-end ${changeClass}">
                            ${update.change} (${update.change_percent}%)
                        </td>
                    </tr>
                `;
            });
            
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }
        
        html += `
            <div class="alert alert-info mb-0">
                <h6 class="mb-2">Summary</h6>
                <div class="row">
                    <div class="col-6">
                        <small class="text-muted">Previous Balance</small><br>
                        <strong>${report.previous_balance}</strong>
                    </div>
                    <div class="col-6">
                        <small class="text-muted">New Balance</small><br>
                        <strong>${report.new_balance}</strong>
                    </div>
                </div>
            </div>
        `;
        
        reportDiv.innerHTML = html;
        
        const modal = new bootstrap.Modal(document.getElementById('monthAdvanceModal'));
        modal.show();
    },
    
    // Undo month
    async undoMonth() {
        if (!confirm('⚠️ UNDO CURRENT MONTH?\n\nThis will:\n• Restore balance to start of month\n• Restore holdings to start of month\n• Delete all operations (except dividends)\n\nThis cannot be undone. Continue?')) {
            return;
        }
        
        try {
            Utils.showLoading();
            
            await API.snapshot.restore(this.simulation.id);
            
            Utils.hideLoading();
            Utils.showToast('Month undone successfully!', 'success');
            
            await this.loadAllData();
            
        } catch (error) {
            Utils.hideLoading();
            Utils.showToast('Failed to undo: ' + error.message, 'error');
        }
    },
    
    // Toggle history
    toggleHistory() {
        const content = document.getElementById('historyContent');
        const btn = document.getElementById('toggleHistoryBtn');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.innerHTML = '<i class="bi bi-chevron-up"></i> Hide';
            this.renderHistory();
        } else {
            content.style.display = 'none';
            btn.innerHTML = '<i class="bi bi-chevron-down"></i> Show';
        }
    },
    
    // Render history
    renderHistory() {
        const timeline = document.getElementById('historyTimeline');
        
        if (!this.history.months || this.history.months.length === 0) {
            timeline.innerHTML = '<p class="text-muted text-center py-3">No transaction history yet.</p>';
            return;
        }
        
        let html = '';
        
        const months = [...this.history.months].reverse();
        
        months.forEach(month => {
            html += `
                <div class="history-month">
                    <div class="history-month-header">
                        <span>${Utils.formatDate(month.month_date)}</span>
                        <span class="fw-bold">Balance: ${month.total}</span>
                    </div>
            `;
            
            if (month.operations.length === 0) {
                html += '<p class="text-muted small mb-0">No operations this month</p>';
            } else {
                month.operations.forEach(op => {
                    const icon = {
                        'contribution': 'plus-circle text-success',
                        'withdrawal': 'dash-circle text-danger',
                        'purchase': 'cart-plus text-primary',
                        'sale': 'cart-dash text-warning',
                        'dividend': 'coin text-success'
                    }[op.type] || 'circle';
                    
                    html += `
                        <div class="history-operation">
                            <i class="bi bi-${icon}"></i>
                            <strong>${op.type.charAt(0).toUpperCase() + op.type.slice(1)}</strong>
                            ${op.ticker ? `(${op.ticker})` : ''}
                            : ${op.amount}
                        </div>
                    `;
                });
            }
            
            html += '</div>';
        });
        
        timeline.innerHTML = html;
    }
};