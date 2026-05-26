import { FileText } from "lucide-react";

import { UploadForm } from "@/components/documents/UploadForm";

export default function DocumentsPage() {
  return (
    <div className="flex flex-col h-screen">
      <div className="border-b bg-white px-6 py-3.5">
        <h1 className="font-semibold text-gray-900">Documents</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Upload files to your knowledge base — indexed asynchronously via SQS
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 max-w-2xl">
        <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 flex gap-3 mb-6 text-sm text-blue-700">
          <FileText className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Async indexing</p>
            <p className="text-blue-600 text-xs mt-0.5">
              Uploaded files are sent to an SQS queue and chunked + embedded in the
              background. They become searchable within ~30 seconds.
            </p>
          </div>
        </div>

        <UploadForm />
      </div>
    </div>
  );
}
