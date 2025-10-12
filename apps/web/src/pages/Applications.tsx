import ApplicationsList from "@/components/ApplicationsList"

/**
 * ApplicationsPage - Demo page for paginated applications list
 * 
 * This page demonstrates the new cursor-based pagination with
 * BigQuery/Elasticsearch/Demo backend support.
 */
export default function ApplicationsPage() {
  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Applications</h1>
        <p className="text-gray-600">
          Paginated applications list with sorting and filtering
        </p>
      </div>

      <ApplicationsList />
    </div>
  )
}
