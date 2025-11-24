export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Data Agent V4
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Multi-tenant SaaS Platform for Intelligent Data Analysis
          </p>
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-md mx-auto">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              Welcome to Data Agent V4
            </h2>
            <p className="text-gray-600 mb-6">
              Your intelligent data analysis platform is currently being initialized.
            </p>
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
              <p className="text-sm">
                ✅ Frontend successfully initialized with Next.js 14+
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}