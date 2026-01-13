const API_BASE = 'http://localhost:5000/api';

// State
let currentPage = 1;
const pageSize = 50;
let currentFilters = {};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeButtons();
    loadTransactions();
    loadCategories();
    loadSources();
});

// Tab navigation
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(tabName).classList.add('active');

            // Load data for specific tabs
            if (tabName === 'statistics') {
                loadStatistics();
            } else if (tabName === 'contributions') {
                loadContributions();
                loadContributionStatistics();
                loadPersonMappings();
                populatePersonFilter();
            } else if (tabName === 'projections') {
                loadProjectionData();
            }
        });
    });
}

// Initialize button handlers
function initializeButtons() {
    document.getElementById('refreshBtn').addEventListener('click', refreshAll);
    document.getElementById('importCsvBtn').addEventListener('click', () => openModal('importModal'));
    document.getElementById('scrapBtn').addEventListener('click', () => openModal('scrapeModal'));

    // Import modal
    document.getElementById('confirmImportBtn').addEventListener('click', importCsv);
    document.getElementById('cancelImportBtn').addEventListener('click', () => closeModal('importModal'));

    // Scrape modal
    document.getElementById('confirmScrapeBtn').addEventListener('click', scrapeTransactions);
    document.getElementById('cancelScrapeBtn').addEventListener('click', () => closeModal('scrapeModal'));

    // Transaction filters
    document.getElementById('searchBtn').addEventListener('click', searchTransactions);
    document.getElementById('clearFiltersBtn').addEventListener('click', clearFilters);

    // Statistics
    document.getElementById('updateStatsBtn').addEventListener('click', loadStatistics);

    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => changePage(-1));
    document.getElementById('nextPage').addEventListener('click', () => changePage(1));

    // Projections
    document.getElementById('calculateProjectionBtn').addEventListener('click', calculateProjection);

    // Contributions
    document.getElementById('addMappingBtn').addEventListener('click', addPersonMapping);
    document.getElementById('filterContributionsBtn').addEventListener('click', filterContributions);
    document.getElementById('clearContribFiltersBtn').addEventListener('click', clearContributionFilters);
}

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// API calls
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'API call failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        alert(`Error: ${error.message}`);
        throw error;
    }
}

// Deposits by source display (used by Statistics tab)
function displayDepositsBySource(deposits, containerId) {
    const container = document.getElementById(containerId);
    if (!deposits || deposits.length === 0) {
        container.innerHTML = '<p class="loading">No deposit data available</p>';
        return;
    }

    container.innerHTML = deposits.map(deposit => `
        <div class="list-item">
            <span class="list-item-label">${deposit.source || 'Unknown'} (${deposit.count} transactions)</span>
            <span class="list-item-value positive">${formatCurrency(deposit.total)}</span>
        </div>
    `).join('');
}

function displayMonthlyBreakdown(monthly, containerId) {
    const container = document.getElementById(containerId);
    if (!monthly || monthly.length === 0) {
        container.innerHTML = '<p class="loading">No monthly data available</p>';
        return;
    }

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Month</th>
                    <th>Deposits</th>
                    <th>Withdrawals</th>
                    <th>Net</th>
                </tr>
            </thead>
            <tbody>
                ${monthly.map(month => `
                    <tr>
                        <td>${month.month}</td>
                        <td class="amount-positive">${formatCurrency(month.deposits)}</td>
                        <td class="amount-negative">${formatCurrency(month.withdrawals)}</td>
                        <td class="${month.net >= 0 ? 'amount-positive' : 'amount-negative'}">${formatCurrency(month.net)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Load transactions
async function loadTransactions() {
    try {
        const offset = (currentPage - 1) * pageSize;
        const transactions = await apiCall(`/transactions?limit=${pageSize}&offset=${offset}`);

        displayTransactions(transactions.data);
        updatePagination(transactions.count);
    } catch (error) {
        console.error('Failed to load transactions:', error);
    }
}

function displayTransactions(transactions) {
    const tbody = document.getElementById('transactionsBody');

    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No transactions found</td></tr>';
        return;
    }

    tbody.innerHTML = transactions.map(txn => `
        <tr>
            <td>${formatDate(txn.transaction_date)}</td>
            <td>${txn.description}</td>
            <td class="${txn.amount >= 0 ? 'amount-positive' : 'amount-negative'}">${formatCurrency(txn.amount)}</td>
            <td>${txn.balance ? formatCurrency(txn.balance) : '-'}</td>
            <td>${txn.category || '-'}</td>
            <td>${txn.source || '-'}</td>
        </tr>
    `).join('');
}

function updatePagination(count) {
    document.getElementById('pageInfo').textContent = `Page ${currentPage}`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = count < pageSize;
}

function changePage(direction) {
    currentPage += direction;
    loadTransactions();
}

// Search transactions
async function searchTransactions() {
    const search = document.getElementById('searchInput').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const category = document.getElementById('categoryFilter').value;
    const source = document.getElementById('sourceFilter').value;

    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (category) params.append('category', category);
    if (source) params.append('source', source);

    try {
        const transactions = await apiCall(`/transactions/search?${params.toString()}`);
        displayTransactions(transactions.data);
    } catch (error) {
        console.error('Search failed:', error);
    }
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('categoryFilter').value = '';
    document.getElementById('sourceFilter').value = '';
    currentPage = 1;
    loadTransactions();
}

// Load categories and sources
async function loadCategories() {
    try {
        const categories = await apiCall('/categories');
        const select = document.getElementById('categoryFilter');
        categories.data.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

async function loadSources() {
    try {
        const sources = await apiCall('/sources');
        const select = document.getElementById('sourceFilter');
        sources.data.forEach(src => {
            const option = document.createElement('option');
            option.value = src;
            option.textContent = src;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load sources:', error);
    }
}

// Statistics tab
async function loadStatistics() {
    const startDate = document.getElementById('statsStartDate').value;
    const endDate = document.getElementById('statsEndDate').value;

    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    try {
        const stats = await apiCall(`/statistics?${params.toString()}`);
        displayStatistics(stats.data);
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

function displayStatistics(stats) {
    document.getElementById('statsTotalTransactions').textContent = stats.total_transactions || 0;
    document.getElementById('statsTotalDeposits').textContent = formatCurrency(stats.total_deposits || 0);
    document.getElementById('statsTotalWithdrawals').textContent = formatCurrency(stats.total_withdrawals || 0);

    const netChange = stats.net_change || 0;
    const netElement = document.getElementById('statsNetChange');
    netElement.textContent = formatCurrency(netChange);
    netElement.className = 'stat-value ' + (netChange >= 0 ? 'positive' : 'negative');

    document.getElementById('statsAvgTransaction').textContent = formatCurrency(stats.avg_transaction || 0);

    const dateRange = stats.earliest_date && stats.latest_date
        ? `${formatDate(stats.earliest_date)} to ${formatDate(stats.latest_date)}`
        : '-';
    document.getElementById('statsDateRange').textContent = dateRange;

    displayDepositsBySource(stats.deposits_by_source, 'statsDepositsBySource');
    displayMonthlyBreakdown(stats.monthly_breakdown, 'statsMonthlyBreakdown');
    displayCategoryBreakdown(stats.by_category);
}

function displayCategoryBreakdown(categories) {
    const container = document.getElementById('statsByCategory');
    if (!categories || categories.length === 0) {
        container.innerHTML = '<p class="loading">No category data available</p>';
        return;
    }

    container.innerHTML = categories.map(cat => `
        <div class="list-item">
            <span class="list-item-label">${cat.category} (${cat.count} transactions)</span>
            <span class="list-item-value ${cat.total >= 0 ? 'positive' : 'negative'}">${formatCurrency(cat.total)}</span>
        </div>
    `).join('');
}

// Import CSV
async function importCsv() {
    const csvPath = document.getElementById('csvPath').value;
    const statusDiv = document.getElementById('importStatus');

    if (!csvPath) {
        alert('Please enter a CSV file path');
        return;
    }

    statusDiv.textContent = 'Importing...';
    statusDiv.className = 'status-message';
    statusDiv.style.display = 'block';

    try {
        const result = await apiCall('/import/csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ csv_path: csvPath })
        });

        statusDiv.textContent = result.message;
        statusDiv.className = 'status-message success';

        setTimeout(() => {
            closeModal('importModal');
            refreshAll();
        }, 2000);
    } catch (error) {
        statusDiv.textContent = `Error: ${error.message}`;
        statusDiv.className = 'status-message error';
    }
}

// Scrape transactions
async function scrapeTransactions() {
    const startDate = document.getElementById('scrapeStartDate').value;
    const endDate = document.getElementById('scrapeEndDate').value;
    const statusDiv = document.getElementById('scrapeStatus');

    statusDiv.textContent = 'Scraping eTrade... This may take a minute.';
    statusDiv.className = 'status-message';
    statusDiv.style.display = 'block';

    try {
        const result = await apiCall('/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });

        statusDiv.textContent = result.message;
        statusDiv.className = 'status-message success';

        setTimeout(() => {
            closeModal('scrapeModal');
            refreshAll();
        }, 2000);
    } catch (error) {
        statusDiv.textContent = `Error: ${error.message}`;
        statusDiv.className = 'status-message error';
    }
}

// Projections

async function loadProjectionData() {
    try {
        // Fetch latest transaction for current balance
        const transactionsResult = await apiCall('/transactions?limit=1');
        const latestTransaction = transactionsResult.data[0];
        const currentBalance = latestTransaction ? latestTransaction.balance : 0;

        // Fetch contribution statistics for monthly average
        const statsResult = await apiCall('/contributions/statistics');
        const byPerson = statsResult.data.by_person || [];
        const monthlyData = statsResult.data.monthly_by_person || [];

        // Calculate average monthly contributions
        let avgMonthlyContributions = 0;
        if (monthlyData.length > 0) {
            // Get unique months
            const uniqueMonths = new Set(monthlyData.map(item => item.month));
            const totalContributions = byPerson.reduce((sum, p) => sum + p.total, 0);
            avgMonthlyContributions = totalContributions / uniqueMonths.size;
        }

        // Fixed recurring withdrawals
        const monthlyWithdrawals = 2605.57; // $1,827.57 + $778
        const monthlyNet = avgMonthlyContributions - monthlyWithdrawals;

        // Update source data display
        document.getElementById('projSourceBalance').textContent = formatCurrency(currentBalance);
        document.getElementById('projSourceDeposits').textContent = formatCurrency(avgMonthlyContributions);
        document.getElementById('projSourceWithdrawals').textContent = formatCurrency(monthlyWithdrawals);

        const monthlyNetElement = document.getElementById('projSourceNet');
        monthlyNetElement.textContent = formatCurrency(monthlyNet);
        monthlyNetElement.className = 'stat-value ' + (monthlyNet >= 0 ? 'positive' : 'negative');

        // Store data for calculateProjection
        window.projectionSourceData = {
            currentBalance,
            avgMonthlyContributions,
            monthlyWithdrawals
        };

    } catch (error) {
        console.error('Failed to load projection data:', error);
    }
}

async function calculateProjection() {
    // Get projection period
    const months = parseInt(document.getElementById('projectionMonths').value) || 12;

    // Use auto-loaded data
    if (!window.projectionSourceData) {
        console.error('Projection source data not loaded');
        return;
    }

    const { currentBalance, avgMonthlyContributions, monthlyWithdrawals } = window.projectionSourceData;

    // Create recurring deposits and withdrawals for API
    const recurringDeposits = [
        {
            description: 'Average Monthly Contributions',
            amount: avgMonthlyContributions,
            frequency: 'monthly'
        }
    ];

    const recurringWithdrawals = [
        {
            description: 'Withdrawal on 1st',
            amount: 1827.57,
            frequency: 'monthly'
        },
        {
            description: 'Withdrawal on 5th',
            amount: 778.00,
            frequency: 'monthly'
        }
    ];

    try {
        const result = await apiCall('/projections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_balance: currentBalance,
                months: months,
                recurring_deposits: recurringDeposits,
                recurring_withdrawals: recurringWithdrawals
            })
        });

        displayProjectionResults(result.data);
    } catch (error) {
        console.error('Projection calculation failed:', error);
    }
}

function displayProjectionResults(data) {
    document.getElementById('projectionResults').classList.remove('hidden');

    const summary = data.summary;
    document.getElementById('projCurrentBalance').textContent = formatCurrency(summary.current_balance);
    document.getElementById('projFinalBalance').textContent = formatCurrency(summary.final_balance);

    const totalChange = summary.total_change;
    const totalChangeElement = document.getElementById('projTotalChange');
    totalChangeElement.textContent = formatCurrency(totalChange);
    totalChangeElement.className = 'stat-value ' + (totalChange >= 0 ? 'positive' : 'negative');

    const monthlyNet = summary.monthly_net;
    const monthlyNetElement = document.getElementById('projMonthlyNet');
    monthlyNetElement.textContent = formatCurrency(monthlyNet);
    monthlyNetElement.className = 'stat-value ' + (monthlyNet >= 0 ? 'positive' : 'negative');

    const chartContainer = document.getElementById('projectionChart');
    chartContainer.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Month</th>
                    <th>Deposits</th>
                    <th>Withdrawals</th>
                    <th>Net Change</th>
                    <th>Projected Balance</th>
                </tr>
            </thead>
            <tbody>
                ${data.projections.map(proj => `
                    <tr>
                        <td>${proj.month_name}</td>
                        <td class="amount-positive">${formatCurrency(proj.deposits)}</td>
                        <td class="amount-negative">${formatCurrency(proj.withdrawals)}</td>
                        <td class="${proj.net_change >= 0 ? 'amount-positive' : 'amount-negative'}">${formatCurrency(proj.net_change)}</td>
                        <td><strong>${formatCurrency(proj.projected_balance)}</strong></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Contributions Management

async function loadPersonMappings() {
    try {
        const result = await apiCall('/person-mappings');
        displayPersonMappings(result.data);
    } catch (error) {
        console.error('Failed to load person mappings:', error);
    }
}

function displayPersonMappings(mappings) {
    const tbody = document.getElementById('mappingsTableBody');

    if (!mappings || mappings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No person mappings found. Add one above to get started.</td></tr>';
        return;
    }

    tbody.innerHTML = mappings.map(mapping => `
        <tr>
            <td>${mapping.person_name}</td>
            <td>${mapping.keyword}</td>
            <td>${formatDate(mapping.created_at)}</td>
            <td>
                <button class="btn btn-small" onclick="deletePersonMapping(${mapping.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

async function addPersonMapping() {
    const personName = document.getElementById('mappingPersonName').value;
    const keyword = document.getElementById('mappingKeyword').value;

    if (!personName || !keyword) {
        alert('Please enter both person name and keyword');
        return;
    }

    try {
        await apiCall('/person-mappings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                person_name: personName,
                keyword: keyword
            })
        });

        // Clear inputs
        document.getElementById('mappingPersonName').value = '';
        document.getElementById('mappingKeyword').value = '';

        // Refresh all contribution data
        loadPersonMappings();
        loadContributions();
        loadContributionStatistics();
        populatePersonFilter();

        alert('Mapping added successfully!');
    } catch (error) {
        console.error('Failed to add mapping:', error);
        alert(`Error: ${error.message}`);
    }
}

async function deletePersonMapping(mappingId) {
    if (!confirm('Are you sure you want to delete this mapping?')) {
        return;
    }

    try {
        await apiCall(`/person-mappings/${mappingId}`, {
            method: 'DELETE'
        });

        // Refresh all contribution data
        loadPersonMappings();
        loadContributions();
        loadContributionStatistics();
        populatePersonFilter();
    } catch (error) {
        console.error('Failed to delete mapping:', error);
        alert(`Error: ${error.message}`);
    }
}

async function loadContributionStatistics() {
    try {
        const result = await apiCall('/contributions/statistics');
        displayContributionStatistics(result.data);
    } catch (error) {
        console.error('Failed to load contribution statistics:', error);
    }
}

function displayContributionStatistics(stats) {
    // Update summary stats
    const byPerson = stats.by_person || [];
    const totalContributors = byPerson.length;
    const totalAmount = byPerson.reduce((sum, p) => sum + p.total, 0);
    const totalCount = byPerson.reduce((sum, p) => sum + p.count, 0);

    document.getElementById('totalContributors').textContent = totalContributors;
    document.getElementById('totalContributionAmount').textContent = formatCurrency(totalAmount);
    document.getElementById('contributionTxnCount').textContent = totalCount;

    // Calculate monthly averages from monthly_by_person data
    const monthlyData = stats.monthly_by_person || [];
    const monthCountByPerson = {};

    monthlyData.forEach(item => {
        if (!monthCountByPerson[item.person_name]) {
            monthCountByPerson[item.person_name] = new Set();
        }
        monthCountByPerson[item.person_name].add(item.month);
    });

    // Display by person with monthly averages
    const byPersonContainer = document.getElementById('contributionsByPerson');
    if (!byPerson || byPerson.length === 0) {
        byPersonContainer.innerHTML = '<p class="loading">No contribution data available</p>';
    } else {
        byPersonContainer.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Total</th>
                        <th>Monthly Average</th>
                    </tr>
                </thead>
                <tbody>
                    ${byPerson.map(person => {
                        const monthCount = monthCountByPerson[person.person_name] ? monthCountByPerson[person.person_name].size : 1;
                        const monthlyAvg = person.total / monthCount;
                        return `
                            <tr>
                                <td>${person.person_name}</td>
                                <td class="amount-positive">${formatCurrency(person.total)}</td>
                                <td class="amount-positive">${formatCurrency(monthlyAvg)}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;
    }
}

async function loadContributions() {
    try {
        const result = await apiCall('/contributions');
        displayContributions(result.data);
    } catch (error) {
        console.error('Failed to load contributions:', error);
    }
}

function displayContributions(contributions) {
    const tbody = document.getElementById('contributionsTableBody');

    if (!contributions || contributions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No contribution transactions found. Add person mappings to track contributions.</td></tr>';
        return;
    }

    tbody.innerHTML = contributions.map(contrib => `
        <tr>
            <td>${formatDate(contrib.transaction_date)}</td>
            <td>${contrib.person_name}</td>
            <td class="amount-positive">${formatCurrency(contrib.amount)}</td>
            <td>${contrib.balance ? formatCurrency(contrib.balance) : '-'}</td>
            <td>${contrib.description}</td>
        </tr>
    `).join('');
}

async function filterContributions() {
    const personName = document.getElementById('personFilter').value;
    const startDate = document.getElementById('contribStartDate').value;
    const endDate = document.getElementById('contribEndDate').value;

    const params = new URLSearchParams();
    if (personName) params.append('person_name', personName);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    try {
        const result = await apiCall(`/contributions?${params.toString()}`);
        displayContributions(result.data);
    } catch (error) {
        console.error('Filter failed:', error);
    }
}

function clearContributionFilters() {
    document.getElementById('personFilter').value = '';
    document.getElementById('contribStartDate').value = '';
    document.getElementById('contribEndDate').value = '';
    loadContributions();
}

async function populatePersonFilter() {
    try {
        const result = await apiCall('/person-mappings');
        const select = document.getElementById('personFilter');

        // Clear existing options except "All People"
        select.innerHTML = '<option value="">All People</option>';

        // Get unique person names
        const uniquePersons = [...new Set(result.data.map(m => m.person_name))];

        uniquePersons.sort().forEach(person => {
            const option = document.createElement('option');
            option.value = person;
            option.textContent = person;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to populate person filter:', error);
    }
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    // Parse as local date by adding 'T00:00:00' to force local timezone
    const date = new Date(dateString + 'T00:00:00');
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function refreshAll() {
    loadTransactions();
    loadStatistics();
}
