import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
} from 'react-flow-renderer';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Settings, 
  Users, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Ticket,
  Key,
  Camera,
  Mail
} from 'lucide-react';
import './App.css';

// State machine configuration
const STATES = {
  NOT_STARTED: { id: 'not-started', label: 'Not Started', color: 'not-started' },
  FORMS_RAISED: { id: 'forms-raised', label: 'Forms Raised', color: 'forms-raised' },
  CREDS_ISSUED: { id: 'creds-issued', label: 'Creds Issued', color: 'creds-issued' },
  ACCESS_PROVISIONED: { id: 'access-provisioned', label: 'Access Provisioned', color: 'access-provisioned' },
  VALIDATED: { id: 'validated', label: 'Validated', color: 'validated' },
  SIGNOFF_SENT: { id: 'signoff-sent', label: 'Signoff Sent', color: 'signoff-sent' },
  APPROVED: { id: 'approved', label: 'Approved', color: 'approved' },
  COMPLETE: { id: 'complete', label: 'Complete', color: 'complete' },
  BLOCKED: { id: 'blocked', label: 'Blocked', color: 'blocked' },
  CHANGES_REQUESTED: { id: 'changes-requested', label: 'Changes Requested', color: 'changes-requested' }
};

const ENVIRONMENTS = ['dev', 'staging', 'prod'];

// Custom node components
const StateNode = ({ data }) => {
  const { state, environment, evidence, isActive, isCompleted } = data;
  
  return (
    <div className={`state-node ${state.color} ${isActive ? 'ring-2 ring-blue-500' : ''} ${isCompleted ? 'ring-2 ring-green-500' : ''}`}>
      <div className="font-semibold text-sm">{state.label}</div>
      <div className="text-xs text-gray-600 mt-1">{environment.toUpperCase()}</div>
      {evidence && evidence.length > 0 && (
        <div className="mt-2 flex flex-wrap justify-center">
          {evidence.map((item, index) => (
            <span key={index} className={`evidence-badge ${item.type}`}>
              {item.type === 'ticket' && <Ticket size={8} className="inline mr-1" />}
              {item.type === 'secret' && <Key size={8} className="inline mr-1" />}
              {item.type === 'screenshot' && <Camera size={8} className="inline mr-1" />}
              {item.type === 'email' && <Mail size={8} className="inline mr-1" />}
              {item.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

const ApprovalNode = ({ data }) => {
  const { approval, isActive } = data;
  
  return (
    <div className={`approval-node ${approval.status} ${isActive ? 'ring-2 ring-yellow-500' : ''}`}>
      <div className="font-semibold text-sm">🔒 Approval Gate</div>
      <div className="text-xs mt-1">{approval.title}</div>
      <div className="text-xs mt-1">
        <Users size={10} className="inline mr-1" />
        {approval.approvers.length} approvers
      </div>
      <div className="text-xs mt-1">
        <Clock size={10} className="inline mr-1" />
        {approval.timeout}h timeout
      </div>
      {approval.status === 'approved' && (
        <div className="text-xs mt-1 text-green-600">
          <CheckCircle size={10} className="inline mr-1" />
          Approved by {approval.approvedBy}
        </div>
      )}
    </div>
  );
};

const nodeTypes = {
  stateNode: StateNode,
  approvalNode: ApprovalNode,
};

// Initial nodes and edges for the state machine
const initialNodes = [
  // Dev environment
  { id: 'dev-not-started', type: 'stateNode', position: { x: 100, y: 100 }, data: { state: STATES.NOT_STARTED, environment: 'dev', evidence: [] } },
  { id: 'dev-forms-raised', type: 'stateNode', position: { x: 300, y: 100 }, data: { state: STATES.FORMS_RAISED, environment: 'dev', evidence: [] } },
  { id: 'dev-creds-issued', type: 'stateNode', position: { x: 500, y: 100 }, data: { state: STATES.CREDS_ISSUED, environment: 'dev', evidence: [] } },
  { id: 'dev-access-provisioned', type: 'stateNode', position: { x: 700, y: 100 }, data: { state: STATES.ACCESS_PROVISIONED, environment: 'dev', evidence: [] } },
  { id: 'dev-validated', type: 'stateNode', position: { x: 900, y: 100 }, data: { state: STATES.VALIDATED, environment: 'dev', evidence: [] } },
  { id: 'dev-signoff-sent', type: 'stateNode', position: { x: 1100, y: 100 }, data: { state: STATES.SIGNOFF_SENT, environment: 'dev', evidence: [] } },
  { id: 'dev-approved', type: 'stateNode', position: { x: 1300, y: 100 }, data: { state: STATES.APPROVED, environment: 'dev', evidence: [] } },
  { id: 'dev-complete', type: 'stateNode', position: { x: 1500, y: 100 }, data: { state: STATES.COMPLETE, environment: 'dev', evidence: [] } },

  // Staging environment
  { id: 'staging-not-started', type: 'stateNode', position: { x: 100, y: 300 }, data: { state: STATES.NOT_STARTED, environment: 'staging', evidence: [] } },
  { id: 'staging-forms-raised', type: 'stateNode', position: { x: 300, y: 300 }, data: { state: STATES.FORMS_RAISED, environment: 'staging', evidence: [] } },
  { id: 'staging-creds-issued', type: 'stateNode', position: { x: 500, y: 300 }, data: { state: STATES.CREDS_ISSUED, environment: 'staging', evidence: [] } },
  { id: 'staging-access-provisioned', type: 'stateNode', position: { x: 700, y: 300 }, data: { state: STATES.ACCESS_PROVISIONED, environment: 'staging', evidence: [] } },
  { id: 'staging-validated', type: 'stateNode', position: { x: 900, y: 300 }, data: { state: STATES.VALIDATED, environment: 'staging', evidence: [] } },
  { id: 'staging-signoff-sent', type: 'stateNode', position: { x: 1100, y: 300 }, data: { state: STATES.SIGNOFF_SENT, environment: 'staging', evidence: [] } },
  { id: 'staging-approved', type: 'stateNode', position: { x: 1300, y: 300 }, data: { state: STATES.APPROVED, environment: 'staging', evidence: [] } },
  { id: 'staging-complete', type: 'stateNode', position: { x: 1500, y: 300 }, data: { state: STATES.COMPLETE, environment: 'staging', evidence: [] } },

  // Prod environment
  { id: 'prod-not-started', type: 'stateNode', position: { x: 100, y: 500 }, data: { state: STATES.NOT_STARTED, environment: 'prod', evidence: [] } },
  { id: 'prod-forms-raised', type: 'stateNode', position: { x: 300, y: 500 }, data: { state: STATES.FORMS_RAISED, environment: 'prod', evidence: [] } },
  { id: 'prod-creds-issued', type: 'stateNode', position: { x: 500, y: 500 }, data: { state: STATES.CREDS_ISSUED, environment: 'prod', evidence: [] } },
  { id: 'prod-access-provisioned', type: 'stateNode', position: { x: 700, y: 500 }, data: { state: STATES.ACCESS_PROVISIONED, environment: 'prod', evidence: [] } },
  { id: 'prod-validated', type: 'stateNode', position: { x: 900, y: 500 }, data: { state: STATES.VALIDATED, environment: 'prod', evidence: [] } },
  { id: 'prod-signoff-sent', type: 'stateNode', position: { x: 1100, y: 500 }, data: { state: STATES.SIGNOFF_SENT, environment: 'prod', evidence: [] } },
  { id: 'prod-approved', type: 'stateNode', position: { x: 1300, y: 500 }, data: { state: STATES.APPROVED, environment: 'prod', evidence: [] } },
  { id: 'prod-complete', type: 'stateNode', position: { x: 1500, y: 500 }, data: { state: STATES.COMPLETE, environment: 'prod', evidence: [] } },

  // Approval nodes
  { id: 'approval-1', type: 'approvalNode', position: { x: 200, y: 50 }, data: { approval: { title: 'Ticket Creation', approvers: ['ping-admin', 'security'], timeout: 24, status: 'pending' } } },
  { id: 'approval-2', type: 'approvalNode', position: { x: 1200, y: 50 }, data: { approval: { title: 'Dev Sign-off', approvers: ['ping-admin', 'devops'], timeout: 48, status: 'pending' } } },
  { id: 'approval-3', type: 'approvalNode', position: { x: 1200, y: 250 }, data: { approval: { title: 'Staging Sign-off', approvers: ['ping-admin', 'devops'], timeout: 48, status: 'pending' } } },
  { id: 'approval-4', type: 'approvalNode', position: { x: 1200, y: 450 }, data: { approval: { title: 'Production Deployment', approvers: ['ping-admin', 'security', 'cto'], timeout: 72, status: 'pending' } } },
];

const initialEdges = [
  // Dev environment flow
  { id: 'e1', source: 'dev-not-started', target: 'dev-forms-raised', type: 'smoothstep' },
  { id: 'e2', source: 'dev-forms-raised', target: 'dev-creds-issued', type: 'smoothstep' },
  { id: 'e3', source: 'dev-creds-issued', target: 'dev-access-provisioned', type: 'smoothstep' },
  { id: 'e4', source: 'dev-access-provisioned', target: 'dev-validated', type: 'smoothstep' },
  { id: 'e5', source: 'dev-validated', target: 'dev-signoff-sent', type: 'smoothstep' },
  { id: 'e6', source: 'dev-signoff-sent', target: 'dev-approved', type: 'smoothstep' },
  { id: 'e7', source: 'dev-approved', target: 'dev-complete', type: 'smoothstep' },

  // Staging environment flow
  { id: 'e8', source: 'staging-not-started', target: 'staging-forms-raised', type: 'smoothstep' },
  { id: 'e9', source: 'staging-forms-raised', target: 'staging-creds-issued', type: 'smoothstep' },
  { id: 'e10', source: 'staging-creds-issued', target: 'staging-access-provisioned', type: 'smoothstep' },
  { id: 'e11', source: 'staging-access-provisioned', target: 'staging-validated', type: 'smoothstep' },
  { id: 'e12', source: 'staging-validated', target: 'staging-signoff-sent', type: 'smoothstep' },
  { id: 'e13', source: 'staging-signoff-sent', target: 'staging-approved', type: 'smoothstep' },
  { id: 'e14', source: 'staging-approved', target: 'staging-complete', type: 'smoothstep' },

  // Prod environment flow
  { id: 'e15', source: 'prod-not-started', target: 'prod-forms-raised', type: 'smoothstep' },
  { id: 'e16', source: 'prod-forms-raised', target: 'prod-creds-issued', type: 'smoothstep' },
  { id: 'e17', source: 'prod-creds-issued', target: 'prod-access-provisioned', type: 'smoothstep' },
  { id: 'e18', source: 'prod-access-provisioned', target: 'prod-validated', type: 'smoothstep' },
  { id: 'e19', source: 'prod-validated', target: 'prod-signoff-sent', type: 'smoothstep' },
  { id: 'e20', source: 'prod-signoff-sent', target: 'prod-approved', type: 'smoothstep' },
  { id: 'e21', source: 'prod-approved', target: 'prod-complete', type: 'smoothstep' },

  // Environment progression
  { id: 'e22', source: 'dev-complete', target: 'staging-not-started', type: 'smoothstep', style: { stroke: '#10b981', strokeWidth: 3 } },
  { id: 'e23', source: 'staging-complete', target: 'prod-not-started', type: 'smoothstep', style: { stroke: '#10b981', strokeWidth: 3 } },

  // Approval connections
  { id: 'e24', source: 'approval-1', target: 'dev-forms-raised', type: 'smoothstep', style: { stroke: '#f59e0b', strokeDasharray: '5,5' } },
  { id: 'e25', source: 'dev-signoff-sent', target: 'approval-2', type: 'smoothstep', style: { stroke: '#f59e0b', strokeDasharray: '5,5' } },
  { id: 'e26', source: 'staging-signoff-sent', target: 'approval-3', type: 'smoothstep', style: { stroke: '#f59e0b', strokeDasharray: '5,5' } },
  { id: 'e27', source: 'prod-signoff-sent', target: 'approval-4', type: 'smoothstep', style: { stroke: '#f59e0b', strokeDasharray: '5,5' } },
];

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedClient, setSelectedClient] = useState('Galaxy');
  const [demoLog, setDemoLog] = useState([]);

  // Demo steps configuration
  const demoSteps = [
    {
      name: 'Onboard Galaxy',
      action: () => updateNodeState('dev-not-started', 'forms-raised', [
        { type: 'ticket', label: 'NSSR' },
        { type: 'ticket', label: 'GLAM' }
      ]),
      log: '🚀 Created onboarding thread for Galaxy'
    },
    {
      name: 'Credentials Issued',
      action: () => updateNodeState('dev-forms-raised', 'creds-issued', [
        { type: 'secret', label: '****2345' }
      ]),
      log: '🔐 Credentials issued and stored securely'
    },
    {
      name: 'Access Provisioned',
      action: () => updateNodeState('dev-creds-issued', 'access-provisioned', []),
      log: '👥 GLAM/GWAM access provisioned for dev team'
    },
    {
      name: 'Validation Complete',
      action: () => updateNodeState('dev-access-provisioned', 'validated', [
        { type: 'screenshot', label: 'Login' },
        { type: 'screenshot', label: 'Consent' },
        { type: 'screenshot', label: 'Landing' },
        { type: 'screenshot', label: 'Token' }
      ]),
      log: '📸 All validation screenshots captured'
    },
    {
      name: 'Sign-off Sent',
      action: () => updateNodeState('dev-validated', 'signoff-sent', [
        { type: 'email', label: 'Sign-off' }
      ]),
      log: '📧 Sign-off email sent to approvers'
    },
    {
      name: 'Dev Approved',
      action: () => {
        updateApprovalStatus('approval-2', 'approved', 'ping-admin');
        updateNodeState('dev-signoff-sent', 'approved', []);
      },
      log: '✅ Dev environment approved by ping-admin'
    },
    {
      name: 'Dev Complete',
      action: () => updateNodeState('dev-approved', 'complete', []),
      log: '🎉 Dev environment completed successfully'
    },
    {
      name: 'Start Staging',
      action: () => updateNodeState('staging-not-started', 'forms-raised', [
        { type: 'ticket', label: 'NSSR' },
        { type: 'ticket', label: 'GLAM' }
      ]),
      log: '🚀 Starting staging environment setup'
    }
  ];

  const updateNodeState = (nodeId, newState, evidence) => {
    setNodes(nds => nds.map(node => {
      if (node.id === nodeId) {
        const stateKey = newState.toUpperCase().replace('-', '_');
        return {
          ...node,
          data: {
            ...node.data,
            state: STATES[stateKey],
            evidence: evidence || [],
            isActive: true
          }
        };
      }
      return {
        ...node,
        data: {
          ...node.data,
          isActive: false
        }
      };
    }));
  };

  const updateApprovalStatus = (nodeId, status, approvedBy) => {
    setNodes(nds => nds.map(node => {
      if (node.id === nodeId) {
        return {
          ...node,
          data: {
            ...node.data,
            approval: {
              ...node.data.approval,
              status,
              approvedBy
            },
            isActive: true
          }
        };
      }
      return node;
    }));
  };

  const addLogEntry = (message) => {
    setDemoLog(prev => [...prev, {
      id: Date.now(),
      message,
      timestamp: new Date().toLocaleTimeString()
    }]);
  };

  const playDemo = useCallback(() => {
    if (currentStep < demoSteps.length) {
      const step = demoSteps[currentStep];
      step.action();
      addLogEntry(step.log);
      setCurrentStep(prev => prev + 1);
    } else {
      setIsPlaying(false);
    }
  }, [currentStep, demoSteps]);

  useEffect(() => {
    let interval;
    if (isPlaying) {
      interval = setInterval(playDemo, 2000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, playDemo]);

  const handlePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentStep(0);
    setNodes(initialNodes);
    setEdges(initialEdges);
    setDemoLog([]);
  };

  const handleStepForward = () => {
    if (currentStep < demoSteps.length) {
      playDemo();
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Ping SSO Onboarding Agent</h1>
            <p className="text-gray-600">Visual State Machine Demo</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <button
                onClick={handlePlay}
                className={`px-4 py-2 rounded-lg font-medium ${
                  isPlaying 
                    ? 'bg-red-500 text-white hover:bg-red-600' 
                    : 'bg-green-500 text-white hover:bg-green-600'
                }`}
              >
                {isPlaying ? <Pause size={16} className="inline mr-2" /> : <Play size={16} className="inline mr-2" />}
                {isPlaying ? 'Pause' : 'Play'}
              </button>
              <button
                onClick={handleStepForward}
                disabled={currentStep >= demoSteps.length}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Step →
              </button>
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg font-medium hover:bg-gray-600"
              >
                <RotateCcw size={16} className="inline mr-2" />
                Reset
              </button>
            </div>
            <div className="text-sm text-gray-600">
              Step {currentStep + 1} of {demoSteps.length}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Main Flow Area */}
        <div className="flex-1">
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-left"
            >
              <Controls />
              <MiniMap 
                nodeColor={(node) => {
                  if (node.data?.state) {
                    const colorMap = {
                      'not-started': '#9ca3af',
                      'forms-raised': '#f59e0b',
                      'creds-issued': '#3b82f6',
                      'access-provisioned': '#10b981',
                      'validated': '#6366f1',
                      'signoff-sent': '#ec4899',
                      'approved': '#22c55e',
                      'complete': '#16a34a',
                      'blocked': '#ef4444',
                      'changes-requested': '#f87171'
                    };
                    return colorMap[node.data.state.color] || '#9ca3af';
                  }
                  return '#f59e0b';
                }}
              />
              <Background />
            </ReactFlow>
          </ReactFlowProvider>
        </div>

        {/* Sidebar */}
        <div className="w-80 bg-white shadow-lg border-l">
          <div className="p-4 border-b">
            <h3 className="font-semibold text-gray-900">Demo Controls</h3>
          </div>
          
          <div className="p-4 border-b">
            <h4 className="font-medium text-gray-700 mb-2">Current Client</h4>
            <select 
              value={selectedClient} 
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="Galaxy">Galaxy</option>
              <option value="BusinessBanking">BusinessBanking</option>
              <option value="FinTechApp">FinTechApp</option>
            </select>
          </div>

          <div className="p-4 border-b">
            <h4 className="font-medium text-gray-700 mb-2">Progress</h4>
            <div className="space-y-2">
              {demoSteps.map((step, index) => (
                <div 
                  key={index}
                  className={`p-2 rounded text-sm ${
                    index < currentStep 
                      ? 'bg-green-100 text-green-800' 
                      : index === currentStep 
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {index < currentStep && <CheckCircle size={14} className="inline mr-2" />}
                  {index === currentStep && <AlertCircle size={14} className="inline mr-2" />}
                  {step.name}
                </div>
              ))}
            </div>
          </div>

          <div className="p-4">
            <h4 className="font-medium text-gray-700 mb-2">Activity Log</h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {demoLog.map((entry) => (
                <div key={entry.id} className="text-sm p-2 bg-gray-50 rounded">
                  <div className="text-gray-500 text-xs">{entry.timestamp}</div>
                  <div className="text-gray-800">{entry.message}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
