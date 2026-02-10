interface Props {
  left: string
  right: string
  leftLabel?: string
  rightLabel?: string
}

export default function PromptDiff({ left, right, leftLabel = 'Before', rightLabel = 'After' }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h4 className="text-sm font-medium text-gray-500 mb-2">{leftLabel}</h4>
        <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm whitespace-pre-wrap overflow-auto max-h-96">
          {left}
        </pre>
      </div>
      <div>
        <h4 className="text-sm font-medium text-gray-500 mb-2">{rightLabel}</h4>
        <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm whitespace-pre-wrap overflow-auto max-h-96">
          {right}
        </pre>
      </div>
    </div>
  )
}
