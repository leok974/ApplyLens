/**
 * Rule Builder - Visual interface for creating and editing policy rules
 */

import { useState } from 'react'
import { Plus, Trash2, Edit } from 'lucide-react'
import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { RuleEditorDialog } from './RuleEditorDialog'
import type { PolicyRule } from '../../lib/policyClient'

interface RuleBuilderProps {
  rules: PolicyRule[]
  onAddRule: (rule: PolicyRule) => void
  onUpdateRule: (index: number, rule: PolicyRule) => void
  onDeleteRule: (index: number) => void
}

export function RuleBuilder({
  rules,
  onAddRule,
  onUpdateRule,
  onDeleteRule,
}: RuleBuilderProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  const handleEdit = (index: number) => {
    setEditingIndex(index)
  }

  const handleSaveEdit = (rule: PolicyRule) => {
    if (editingIndex !== null) {
      onUpdateRule(editingIndex, rule)
      setEditingIndex(null)
    }
  }

  const handleSaveNew = (rule: PolicyRule) => {
    onAddRule(rule)
    setIsCreating(false)
  }

  return (
    <div className="space-y-4">
      {/* Add Rule Button */}
      <Button onClick={() => setIsCreating(true)}>
        <Plus className="mr-2 h-4 w-4" />
        Add Rule
      </Button>

      {/* Rules List */}
      {rules.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-muted-foreground py-8">
              <p>No rules yet. Click "Add Rule" to create your first rule.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {rules.map((rule, index) => (
            <Card key={index}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-base font-mono">
                      {rule.id}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {rule.reason}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(index)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDeleteRule(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">Agent:</span>
                    <div className="font-mono">{rule.agent}</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Action:</span>
                    <div className="font-mono">{rule.action}</div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Effect:</span>
                    <div>
                      <Badge
                        variant={
                          rule.effect === 'allow'
                            ? 'default'
                            : rule.effect === 'deny'
                            ? 'destructive'
                            : 'secondary'
                        }
                      >
                        {rule.effect}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Priority:</span>
                    <div className="font-mono">{rule.priority}</div>
                  </div>
                </div>
                {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <span className="text-sm text-muted-foreground">Conditions:</span>
                    <div className="mt-1 space-y-1">
                      {Object.entries(rule.conditions).map(([key, value]) => (
                        <div key={key} className="text-sm font-mono">
                          {key}: <span className="text-primary">{JSON.stringify(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      {editingIndex !== null && (
        <RuleEditorDialog
          rule={rules[editingIndex]}
          open={true}
          onClose={() => setEditingIndex(null)}
          onSave={handleSaveEdit}
        />
      )}

      {/* Create Dialog */}
      {isCreating && (
        <RuleEditorDialog
          rule={null}
          open={true}
          onClose={() => setIsCreating(false)}
          onSave={handleSaveNew}
        />
      )}
    </div>
  )
}
