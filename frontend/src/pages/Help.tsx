import { useState } from 'react'
import {
  ChevronDown, ChevronRight,
  LayoutDashboard, Wallet, ArrowLeftRight, Upload,
  BarChart2, TrendingUp, Settings, HelpCircle,
  PlusCircle, ClipboardList, AlertCircle, CheckCircle2,
  FileSpreadsheet, Target, Calculator, Shield,
} from 'lucide-react'
import PageHeader from '../components/PageHeader'

interface Section {
  id: string
  icon: React.ReactNode
  title: string
  subtitle: string
  color: string
  items: HelpItem[]
}

interface HelpItem {
  title: string
  badge?: string
  badgeColor?: string
  body: React.ReactNode
}

const sections: Section[] = [
  {
    id: 'dashboard',
    icon: <LayoutDashboard size={18} />,
    title: 'Dashboard',
    subtitle: 'Your financial overview at a glance',
    color: 'text-blue-400',
    items: [
      {
        title: 'Total Net Worth card',
        badge: 'Most important number',
        badgeColor: 'badge-blue',
        body: (
          <>
            <p>Your total net worth is <strong>everything you own minus everything you owe</strong>. It combines all your investment accounts, retirement accounts, cash, crypto, and real estate — then subtracts any liabilities you've recorded.</p>
            <p className="mt-2">The green/red number below it shows <strong>how much it changed versus last month's snapshot</strong>. This only updates when you record a net worth snapshot in Settings.</p>
            <Tip>Think of this as your financial "score." Tracking it monthly gives you a clear picture of whether you're building wealth over time.</Tip>
          </>
        ),
      },
      {
        title: 'Investments card',
        body: (
          <>
            <p>The total value of your <strong>taxable brokerage accounts</strong> (Robinhood, Schwab, Fidelity, etc.). This comes from net worth snapshots you record manually in Settings, combined with any manual account entries.</p>
            <p className="mt-2">Note: This does <em>not</em> pull live prices. You update it by recording a snapshot.</p>
          </>
        ),
      },
      {
        title: 'Retirement card',
        body: (
          <p>The combined value of all retirement accounts — <strong>401(k), Roth IRA, Traditional IRA, SEP IRA, HSA, FSA</strong>. Since you can't import most retirement files directly, these are typically tracked via Manual Account entries on the Accounts page, then included in your net worth snapshot.</p>
        ),
      },
      {
        title: 'Cash, Crypto, Real Estate cards',
        body: (
          <>
            <p>These pull from <strong>Manual Account entries</strong> where the account name contains keywords:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li><strong>Cash:</strong> account names containing "savings", "checking", or "cash"</li>
              <li><strong>Crypto:</strong> account names containing "crypto"</li>
              <li><strong>Real Estate:</strong> account names containing "real estate" or "property"</li>
            </ul>
            <Tip>Name your manual accounts clearly (e.g. "Crypto - Coinbase", "Real Estate Equity") so they categorize correctly.</Tip>
          </>
        ),
      },
      {
        title: 'YTD Change',
        body: (
          <p>How much your net worth has changed <strong>since January 1st of this year</strong>, in dollars and as a percentage. Calculated by comparing today's snapshot to the first snapshot recorded this year. If no snapshot exists from this year yet, it shows $0.</p>
        ),
      },
      {
        title: 'Net Worth Over Time chart',
        body: (
          <>
            <p>A line chart of your net worth history built from every snapshot you've recorded. Use the period buttons (<strong>1M, 3M, 1Y, 5Y, ALL</strong>) to zoom in or out.</p>
            <p className="mt-2">The chart only shows data points you've recorded — it won't fill in gaps automatically. Record a snapshot monthly for the best picture.</p>
          </>
        ),
      },
      {
        title: 'Asset Allocation pie chart',
        body: (
          <p>Shows how your wealth is divided across Investments, Retirement, Cash, Crypto, and Real Estate. A healthy allocation for most people skews heavily toward Investments + Retirement. Use this to spot if too much is sitting in cash or too little in retirement.</p>
        ),
      },
    ],
  },
  {
    id: 'accounts',
    icon: <Wallet size={18} />,
    title: 'Accounts',
    subtitle: 'Two ways to track your accounts — know which to use when',
    color: 'text-emerald-400',
    items: [
      {
        title: 'Add Account — what it is',
        badge: 'For brokerage imports',
        badgeColor: 'badge-green',
        body: (
          <>
            <p>"Add Account" creates a <strong>named account that transactions can be imported into</strong>. Think of it as a folder. When you upload a broker CSV file on the Uploads page, you select which account those transactions belong to.</p>
            <p className="mt-2">You only need to create an account here once per broker account you have (e.g. "My Fidelity Brokerage", "Spouse Schwab IRA"). After that, every upload just references the same account.</p>
            <Tip>Create an account here first, then go to Uploads to import your transaction file into it.</Tip>
          </>
        ),
      },
      {
        title: 'Manual Entry — what it is',
        badge: 'For retirement, crypto, cash',
        badgeColor: 'badge-blue',
        body: (
          <>
            <p>"Manual Entry" records the <strong>current dollar value</strong> of an account at a point in time. No transactions needed. Use this for accounts where you can't download a CSV file, or where a simple balance is enough:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li>401(k) at your employer (can't export transactions)</li>
              <li>HSA balance</li>
              <li>Crypto wallet total</li>
              <li>Savings / checking account balances</li>
              <li>Real estate equity (home value minus mortgage)</li>
            </ul>
            <p className="mt-2">Each entry is timestamped. You can add a new entry whenever the value changes — older entries stay in history.</p>
          </>
        ),
      },
      {
        title: 'Add Account vs Manual Entry — when to use which',
        badge: 'Key difference',
        badgeColor: 'badge-blue',
        body: (
          <div className="overflow-x-auto">
            <table className="w-full text-sm mt-1 border-collapse">
              <thead>
                <tr className="border-b border-slate-600">
                  <th className="text-left py-2 pr-4 text-slate-300 font-medium">Situation</th>
                  <th className="text-left py-2 pr-4 text-slate-300 font-medium">Use</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {[
                  ['You have a Robinhood, Schwab, Fidelity, Vanguard, Webull, or E*TRADE account', 'Add Account → then Upload transactions'],
                  ['You have a 401(k) at your employer', 'Manual Entry with the current balance'],
                  ['You want to track your crypto wallet total', 'Manual Entry'],
                  ['You have a Roth IRA you can export from', 'Add Account (type = Roth IRA) → Upload'],
                  ['You have a Roth IRA with no export', 'Manual Entry'],
                  ['Savings or checking account', 'Manual Entry'],
                  ['Real estate equity', 'Manual Entry (home value − mortgage balance)'],
                ].map(([sit, use], i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 text-slate-400">{sit}</td>
                    <td className="py-2 text-slate-200 font-medium">{use}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      },
      {
        title: 'Account Type and Tax Status',
        body: (
          <>
            <p>When adding an account, you set its <strong>type</strong> (brokerage, Roth IRA, 401k, etc.) and <strong>tax status</strong>. The tax status is pre-filled based on account type but you can override it:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li><strong>Taxable:</strong> regular brokerage — gains/dividends are taxed</li>
              <li><strong>Tax Deferred:</strong> 401k, Traditional IRA — taxed on withdrawal</li>
              <li><strong>Tax Free:</strong> Roth IRA, HSA — no tax on qualified withdrawals</li>
            </ul>
            <Tip>Getting this right helps the Projections page give you more accurate retirement estimates.</Tip>
          </>
        ),
      },
      {
        title: 'Owner (Self / Spouse / Joint)',
        body: (
          <p>Every account and manual entry is tagged with an owner. This lets you filter the dashboard to see just your accounts, just your spouse's, or combined. Use <strong>Joint</strong> for shared accounts like a joint brokerage or joint savings.</p>
        ),
      },
    ],
  },
  {
    id: 'transactions',
    icon: <ArrowLeftRight size={18} />,
    title: 'Transactions',
    subtitle: 'Your full imported trading history',
    color: 'text-violet-400',
    items: [
      {
        title: 'What transactions are shown',
        body: (
          <p>Every trade, dividend, deposit, and withdrawal imported from your broker files appears here. Transactions are stored permanently in Google Sheets. The table shows the 500 most recent by default — use filters to narrow down.</p>
        ),
      },
      {
        title: 'Transaction types explained',
        body: (
          <div className="overflow-x-auto">
            <table className="w-full text-sm mt-1 border-collapse">
              <thead>
                <tr className="border-b border-slate-600">
                  <th className="text-left py-2 pr-4 text-slate-300 font-medium">Type</th>
                  <th className="text-left py-2 text-slate-300 font-medium">Meaning</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {[
                  ['BUY', 'You purchased shares of a stock or ETF'],
                  ['SELL', 'You sold shares'],
                  ['DIVIDEND', 'Cash dividend received (or reinvested)'],
                  ['INTEREST', 'Interest income (money market, bonds, cash)'],
                  ['OPTION_BUY', 'Bought an options contract (BTO / Buy to Open)'],
                  ['OPTION_SELL', 'Sold or closed an options position'],
                  ['DEPOSIT', 'Cash deposited into the account'],
                  ['WITHDRAWAL', 'Cash withdrawn from the account'],
                  ['TRANSFER', 'Shares or cash moved between accounts'],
                  ['SPLIT', 'Stock split (share count adjusted, no cash)'],
                ].map(([t, m], i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4"><span className="badge-blue font-mono">{t}</span></td>
                    <td className="py-2 text-slate-400">{m}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      },
      {
        title: 'Using filters',
        body: (
          <>
            <p>Click the <strong>Filters</strong> button to filter by:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li><strong>Ticker:</strong> e.g. "AAPL" to see all Apple trades</li>
              <li><strong>Broker:</strong> e.g. "Fidelity" to see only Fidelity transactions</li>
              <li><strong>Date range:</strong> From / To dates to zoom into a period</li>
            </ul>
          </>
        ),
      },
    ],
  },
  {
    id: 'uploads',
    icon: <Upload size={18} />,
    title: 'Uploads',
    subtitle: 'Import broker CSV and XLSX files',
    color: 'text-amber-400',
    items: [
      {
        title: 'How the import flow works',
        body: (
          <>
            <p>Uploading a broker file takes 3 steps:</p>
            <ol className="mt-2 space-y-2 text-slate-400 text-sm list-decimal list-inside">
              <li><strong>Drop or select your file</strong> — CSV or XLSX from your broker</li>
              <li><strong>Select the broker and account</strong> — tells the parser how to read the file's columns</li>
              <li><strong>Preview then confirm</strong> — review the parsed rows before saving anything</li>
            </ol>
            <p className="mt-2">Duplicate transactions are automatically detected and skipped using a fingerprint of date + ticker + quantity + amount. You'll see a count of how many were imported vs skipped.</p>
          </>
        ),
      },
      {
        title: 'Where to download broker files',
        body: (
          <div className="overflow-x-auto">
            <table className="w-full text-sm mt-1 border-collapse">
              <thead>
                <tr className="border-b border-slate-600">
                  <th className="text-left py-2 pr-4 text-slate-300 font-medium">Broker</th>
                  <th className="text-left py-2 text-slate-300 font-medium">Where to export</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {[
                  ['Robinhood', 'Account → Statements & History → Download CSV'],
                  ['Schwab', 'Accounts → History tab → Export (top right)'],
                  ['Fidelity', 'Activity & Orders → Download → CSV'],
                  ['Vanguard', 'My Accounts → Transaction History → Export to CSV'],
                  ['Webull', 'Orders → Order History → Export'],
                  ['E*TRADE', 'Accounts → Transactions → Download'],
                ].map(([b, w], i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 text-slate-200 font-medium">{b}</td>
                    <td className="py-2 text-slate-400">{w}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      },
      {
        title: 'What if rows are missing or wrong?',
        body: (
          <>
            <p>Broker CSV formats change over time. If the preview shows 0 rows or missing data, try these steps:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li>Make sure you selected the correct broker from the dropdown</li>
              <li>Open the CSV in Excel and check that the first row contains column headers</li>
              <li>Some brokers add account info rows before the header — delete those rows and re-upload</li>
              <li>If the file is XLSX, make sure the data starts on row 1 of the first sheet</li>
            </ul>
          </>
        ),
      },
      {
        title: 'Can I upload the same file twice?',
        body: (
          <p>Yes — duplicates are skipped automatically. Each transaction gets a unique fingerprint based on its date, ticker, quantity, and amount. If a row already exists in Google Sheets with the same fingerprint, it's skipped. You'll see "X skipped (duplicates)" in the result. This means you can re-upload a file after adding new transactions without worrying about double-counting.</p>
        ),
      },
      {
        title: 'Must I create an account before uploading?',
        body: (
          <p>Yes — you need to create an account on the Accounts page first, then select it when uploading. The account acts as a label that groups all transactions from that broker account together. Go to <strong>Accounts → Add Account</strong>, fill in the broker and account name, then come back here to upload.</p>
        ),
      },
    ],
  },
  {
    id: 'analytics',
    icon: <BarChart2 size={18} />,
    title: 'Analytics',
    subtitle: 'Portfolio performance and composition over time',
    color: 'text-cyan-400',
    items: [
      {
        title: 'Net Worth Trend chart',
        body: (
          <p>A multi-line chart showing <strong>total net worth, investments, and retirement</strong> over time. Each dot is a snapshot you recorded. Use the period buttons to zoom in to 1 month, 3 months, 1 year, 5 years, or all time. The dashed lines (Investments, Retirement) help you see which buckets are growing fastest.</p>
        ),
      },
      {
        title: 'Portfolio Composition chart',
        body: (
          <p>A stacked bar chart showing how your <strong>Investments, Retirement, and Cash</strong> balances change over time. If the retirement bar is growing while investments shrink, you may be over-contributing to retirement vs. taxable. Use this to spot allocation shifts.</p>
        ),
      },
      {
        title: 'Why does the chart look empty?',
        body: (
          <>
            <p>Analytics only shows data you've recorded as net worth snapshots. If you haven't recorded any yet, go to <strong>Settings → Record Net Worth Snapshot</strong> and fill in today's values. Snapshots are cumulative — the more often you record them, the richer your charts will be.</p>
            <Tip>Record a snapshot at the start of each month for a clean monthly history.</Tip>
          </>
        ),
      },
    ],
  },
  {
    id: 'projections',
    icon: <TrendingUp size={18} />,
    title: 'Projections',
    subtitle: 'Retirement modeling and FIRE calculations',
    color: 'text-rose-400',
    items: [
      {
        title: 'What is a projection?',
        body: (
          <p>A projection models how your current portfolio will grow over time given a set of assumptions: growth rate, inflation, and monthly contributions. It uses <strong>compound interest math</strong> (not real market data) to estimate your future portfolio value at retirement age.</p>
        ),
      },
      {
        title: 'Current Portfolio Value',
        body: (
          <p>Enter your <strong>total portfolio value today</strong> — this is your starting point. Include everything: brokerage + retirement + savings if you want a full picture. Or enter just your investment accounts if you're projecting only those.</p>
        ),
      },
      {
        title: 'Annual Return %',
        body: (
          <>
            <p>The expected average annual return on your investments. Common benchmarks:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li><strong>5%</strong> — conservative (bonds + stocks mix)</li>
              <li><strong>7%</strong> — historical S&amp;P 500 average (real, inflation-adjusted)</li>
              <li><strong>10%</strong> — historical S&amp;P 500 nominal (before inflation)</li>
              <li><strong>12%+</strong> — aggressive / optimistic</li>
            </ul>
            <Tip>Use 7% for a realistic "market average" projection. Use 5% for a conservative safety margin.</Tip>
          </>
        ),
      },
      {
        title: 'Inflation %',
        body: (
          <p>Inflation reduces your future money's purchasing power. The projection shows both a <strong>nominal value</strong> (the dollar amount) and a <strong>real value</strong> (inflation-adjusted, what it's worth in today's dollars). The Fed's target is 2%. Use 3% for a conservative buffer.</p>
        ),
      },
      {
        title: 'Monthly Contribution',
        body: (
          <p>How much you add to your portfolio each month across all accounts. Include your 401k contributions, IRA contributions, and any taxable brokerage deposits. This is one of the most powerful levers — increasing contributions even slightly has a dramatic long-term effect due to compounding.</p>
        ),
      },
      {
        title: 'FIRE Age — what does it mean?',
        badge: 'FIRE = Financial Independence, Retire Early',
        badgeColor: 'badge-green',
        body: (
          <>
            <p>FIRE Age is the age at which your portfolio is projected to hit the <strong>25× rule</strong> — a common financial independence target. The 25× rule means you've saved 25 times your annual expenses, which at a 4% withdrawal rate would let your money last indefinitely.</p>
            <p className="mt-2">Example: if you spend $60,000/year, your FIRE number is $1,500,000. The FIRE Age is when the projection crosses that threshold.</p>
            <Tip>The FIRE number is estimated from your monthly contribution × 12 × 25. For a more accurate FIRE number, use your actual annual spending, not contributions.</Tip>
          </>
        ),
      },
      {
        title: 'Coast FIRE — what does it mean?',
        badge: 'No more contributions needed',
        badgeColor: 'badge-blue',
        body: (
          <>
            <p>Coast FIRE is the amount you'd need <strong>today</strong> to reach your retirement target by your target age — without contributing another dollar. If you have that amount now, you can "coast" — stop contributing and let compounding do the rest.</p>
            <p className="mt-2">Example: if your target is $2M at age 65, your Coast FIRE at age 35 (30 years away at 7% return) is roughly $263,000. If you already have $263K invested, you don't need to add more to hit $2M.</p>
          </>
        ),
      },
      {
        title: 'Nominal vs Real values on the chart',
        body: (
          <>
            <p><strong>Nominal</strong> (solid blue line) — the actual dollar amount your portfolio is projected to reach. This is what your statement will say.</p>
            <p className="mt-2"><strong>Real / Inflation-adjusted</strong> (dashed purple line) — what that future amount is worth in today's purchasing power. This is the more meaningful number for planning.</p>
            <Tip>Always base retirement planning on the real value, not nominal. $2M in 30 years is only worth ~$1M in today's dollars at 2% inflation.</Tip>
          </>
        ),
      },
      {
        title: 'Saving a scenario',
        body: (
          <p>Click <strong>Save</strong> after running a projection to store it in Google Sheets. Saved scenarios appear in the Projections sheet in your spreadsheet. You can create multiple scenarios (optimistic, conservative, base case) and compare them.</p>
        ),
      },
    ],
  },
  {
    id: 'settings',
    icon: <Settings size={18} />,
    title: 'Settings',
    subtitle: 'Configuration and data management',
    color: 'text-slate-400',
    items: [
      {
        title: 'Record Net Worth Snapshot',
        badge: 'Do this monthly',
        badgeColor: 'badge-green',
        body: (
          <>
            <p>This is the primary way you build your net worth history. Fill in <strong>today's values</strong> for each category:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li><strong>Investments ($):</strong> total value of your taxable brokerage accounts</li>
              <li><strong>Retirement ($):</strong> total of all 401k, IRA, HSA balances</li>
              <li><strong>Cash ($):</strong> savings + checking accounts</li>
              <li><strong>Crypto ($):</strong> total crypto holdings</li>
              <li><strong>Real Estate ($):</strong> home equity (property value minus mortgage)</li>
              <li><strong>Liabilities ($):</strong> debts not already subtracted above (student loans, car loans, credit card balances)</li>
            </ul>
            <p className="mt-2">The snapshot is saved to the <em>Net Worth History</em> sheet in Google Sheets. It powers the Dashboard and Analytics charts.</p>
            <Tip>Set a monthly calendar reminder — "First Sunday: update NetWorth Tracker." Even rough numbers are valuable for long-term trend tracking.</Tip>
          </>
        ),
      },
      {
        title: 'About section',
        body: (
          <p>Shows the app version and a reminder that all credentials are stored in the <code className="font-mono text-slate-300 text-xs">.env</code> file on your laptop — they are never sent to any external service and never committed to GitHub. Your financial data lives in your own Google Sheets spreadsheet.</p>
        ),
      },
    ],
  },
  {
    id: 'google-sheets',
    icon: <FileSpreadsheet size={18} />,
    title: 'Google Sheets (Your Database)',
    subtitle: 'Understanding where your data lives',
    color: 'text-emerald-400',
    items: [
      {
        title: 'How Google Sheets is used',
        body: (
          <p>Google Sheets is the <strong>database</strong> for this app. Every account, transaction, manual entry, and net worth snapshot is stored in your own private spreadsheet — not on any third-party server. You always have full control and can view, edit, or export everything directly in Google Sheets.</p>
        ),
      },
      {
        title: 'The six data tabs',
        body: (
          <div className="overflow-x-auto">
            <table className="w-full text-sm mt-1 border-collapse">
              <thead>
                <tr className="border-b border-slate-600">
                  <th className="text-left py-2 pr-4 text-slate-300 font-medium">Tab</th>
                  <th className="text-left py-2 text-slate-300 font-medium">Stores</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {[
                  ['Accounts', 'All brokerage accounts you\'ve added'],
                  ['Transactions', 'Every imported trade, dividend, and deposit'],
                  ['Holdings Snapshot', 'Point-in-time holdings (for future use)'],
                  ['Manual Accounts', 'Every manual balance entry (401k, crypto, etc.)'],
                  ['Net Worth History', 'Monthly snapshots recorded in Settings'],
                  ['Projections', 'Saved retirement projection scenarios'],
                ].map(([tab, desc], i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 text-slate-200 font-medium font-mono text-xs">{tab}</td>
                    <td className="py-2 text-slate-400">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ),
      },
      {
        title: 'Can I edit data directly in Google Sheets?',
        body: (
          <>
            <p>Yes — since it's just a spreadsheet, you can edit, delete, or fix rows directly in Google Sheets and the changes will reflect in the app on next load. This is useful for correcting import errors.</p>
            <div className="flex items-start gap-2 mt-2 p-3 bg-amber-900/20 border border-amber-700/30 rounded-lg">
              <AlertCircle size={14} className="text-amber-400 mt-0.5 shrink-0" />
              <p className="text-amber-400/90 text-sm">Don't change the column headers in the spreadsheet — the app relies on them to read data correctly.</p>
            </div>
          </>
        ),
      },
    ],
  },
  {
    id: 'security',
    icon: <Shield size={18} />,
    title: 'Security & Privacy',
    subtitle: 'How your credentials and data are protected',
    color: 'text-blue-400',
    items: [
      {
        title: 'Where are my credentials stored?',
        body: (
          <>
            <p>All sensitive credentials are stored <strong>only on your laptop</strong>:</p>
            <ul className="mt-2 space-y-1 text-slate-400 text-sm list-disc list-inside">
              <li><code className="font-mono text-xs text-slate-300">backend/.env</code> — contains your Google Sheets ID and app password</li>
              <li><code className="font-mono text-xs text-slate-300">backend/credentials/service_account.json</code> — your Google service account key</li>
            </ul>
            <p className="mt-2">Both files are in <code className="font-mono text-xs text-slate-300">.gitignore</code> and will <em>never</em> be pushed to GitHub. The GitHub repository contains only code, never data or secrets.</p>
          </>
        ),
      },
      {
        title: 'Who can see my financial data?',
        body: (
          <p>Only you. The app runs entirely on your laptop. Your financial data goes from your laptop to your own private Google Sheets spreadsheet — nowhere else. The Google service account has access only to the specific spreadsheet you shared it with.</p>
        ),
      },
      {
        title: 'What is the login password for?',
        body: (
          <p>The app password (set in <code className="font-mono text-xs text-slate-300">APP_PASSWORD</code> in your <code className="font-mono text-xs text-slate-300">.env</code> file) prevents anyone who accidentally opens <code>localhost:5173</code> on your laptop from viewing your data. It generates a short-lived JWT session token. You can change the password at any time by editing <code className="font-mono text-xs text-slate-300">.env</code> and restarting the backend.</p>
        ),
      },
    ],
  },
]

function Tip({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 mt-3 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
      <CheckCircle2 size={14} className="text-blue-400 mt-0.5 shrink-0" />
      <p className="text-blue-300/90 text-sm">{children}</p>
    </div>
  )
}

function HelpSection({ section }: { section: Section }) {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <div className="card mb-4">
      <div className="flex items-center gap-3 mb-4 pb-4 border-b border-slate-700">
        <span className={section.color}>{section.icon}</span>
        <div>
          <h2 className="text-base font-semibold text-slate-100">{section.title}</h2>
          <p className="text-xs text-slate-400 mt-0.5">{section.subtitle}</p>
        </div>
      </div>

      <div className="space-y-1">
        {section.items.map((item) => {
          const isOpen = open === item.title
          return (
            <div key={item.title} className="rounded-lg overflow-hidden">
              <button
                onClick={() => setOpen(isOpen ? null : item.title)}
                className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-slate-700/40 rounded-lg transition-colors gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {isOpen
                    ? <ChevronDown size={14} className="text-slate-400 shrink-0" />
                    : <ChevronRight size={14} className="text-slate-500 shrink-0" />}
                  <span className="text-sm font-medium text-slate-200 truncate">{item.title}</span>
                  {item.badge && (
                    <span className={`${item.badgeColor ?? 'badge-blue'} shrink-0 hidden sm:inline-flex`}>
                      {item.badge}
                    </span>
                  )}
                </div>
              </button>

              {isOpen && (
                <div className="px-8 pb-4 pt-1 text-sm text-slate-300 leading-relaxed space-y-1">
                  {item.badge && (
                    <span className={`${item.badgeColor ?? 'badge-blue'} mb-2 inline-flex sm:hidden`}>
                      {item.badge}
                    </span>
                  )}
                  {item.body}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Help() {
  const [search, setSearch] = useState('')

  const filtered = search.trim()
    ? sections.map((s) => ({
        ...s,
        items: s.items.filter(
          (item) =>
            item.title.toLowerCase().includes(search.toLowerCase()) ||
            s.title.toLowerCase().includes(search.toLowerCase()),
        ),
      })).filter((s) => s.items.length > 0)
    : sections

  return (
    <div>
      <PageHeader
        title="Help"
        subtitle="Everything you need to know about using NetWorth Tracker"
      />

      <div className="mb-5">
        <input
          className="input max-w-sm"
          placeholder="Search help topics…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {filtered.length === 0 ? (
        <div className="card text-center py-10 text-slate-500">No help topics match "{search}"</div>
      ) : (
        filtered.map((section) => (
          <HelpSection key={section.id} section={section} />
        ))
      )}
    </div>
  )
}
