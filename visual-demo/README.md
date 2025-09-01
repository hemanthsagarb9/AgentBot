# Ping SSO Onboarding Agent - Visual Demo

A React-based visual demonstration of the Ping SSO Onboarding Agent using React Flow to show the state machine, approval workflows, and real-time progress.

## 🎯 Features

- **Interactive State Machine**: Visual representation of the complete onboarding workflow
- **Real-time Animation**: Step-by-step progression through states
- **HITL Approval Gates**: Visual approval nodes with different approver levels
- **Evidence Tracking**: Visual badges showing tickets, secrets, screenshots, emails
- **Multi-Environment**: Dev → Staging → Prod progression
- **Activity Log**: Real-time log of all actions and state changes

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Installation

```bash
# Navigate to visual demo directory
cd visual-demo

# Install dependencies
npm install

# Start the development server
npm start
```

The demo will open at `http://localhost:3000`

## 🎮 Demo Controls

### Playback Controls
- **Play/Pause**: Start or pause the automated demo
- **Step Forward**: Manually advance one step at a time
- **Reset**: Return to initial state

### Client Selection
- Choose from different clients (Galaxy, BusinessBanking, FinTechApp)
- Each client shows independent onboarding progress

### Progress Tracking
- Visual progress bar showing current step
- Activity log with timestamps
- Real-time state updates

## 🎨 Visual Elements

### State Nodes
- **Color-coded states**: Each state has a unique color
- **Evidence badges**: Show tickets, secrets, screenshots, emails
- **Active highlighting**: Current state glows with animation
- **Environment labels**: Clear Dev/Staging/Prod identification

### Approval Gates
- **Dashed borders**: Indicate approval requirements
- **Approver information**: Shows who needs to approve
- **Timeout indicators**: Visual countdown for approvals
- **Status updates**: Approved/rejected states

### Flow Connections
- **State transitions**: Solid lines for normal flow
- **Approval connections**: Dashed lines for HITL gates
- **Environment progression**: Green lines for environment advancement

## 🔄 Demo Scenarios

### Scenario 1: Complete Onboarding Flow
1. **Onboard Galaxy** → Creates thread and tickets
2. **Credentials Issued** → Stores masked secrets
3. **Access Provisioned** → GLAM/GWAM completed
4. **Validation Complete** → All screenshots captured
5. **Sign-off Sent** → Email sent to approvers
6. **Dev Approved** → Human approval granted
7. **Dev Complete** → Ready for next environment
8. **Start Staging** → Begin staging environment

### Scenario 2: HITL Approval Gates
- **Ticket Creation**: Admin + Security approval
- **Dev Sign-off**: Admin + DevOps approval  
- **Staging Sign-off**: Admin + DevOps approval
- **Production Deployment**: Admin + Security + CTO approval

### Scenario 3: Evidence Tracking
- **Tickets**: NSSR, GLAM, GWAM tickets
- **Secrets**: Masked credential references
- **Screenshots**: Login, consent, landing, token
- **Emails**: Sign-off and approval emails

## 🎯 Demo Scripts

### Automated Demo
```bash
# Start the visual demo
npm start

# Use the Play button to run the complete flow
# Watch as states progress through the workflow
# Observe approval gates and evidence collection
```

### Manual Demo
```bash
# Use Step Forward to advance one step at a time
# Explain each state transition and evidence requirement
# Show approval gates and human oversight
# Demonstrate environment progression
```

## 🎨 Customization

### Adding New States
```javascript
// Add to STATES object in App.js
NEW_STATE: { id: 'new-state', label: 'New State', color: 'new-state' }

// Add corresponding CSS class
.state-node.new-state {
  background: #your-color;
  border-color: #your-border-color;
  color: #your-text-color;
}
```

### Adding New Evidence Types
```javascript
// Add to evidence array
{ type: 'new-type', label: 'New Evidence' }

// Add corresponding CSS class
.evidence-badge.new-type {
  background: #your-color;
  color: #your-text-color;
}
```

### Customizing Approval Gates
```javascript
// Modify approval node data
approval: {
  title: 'Custom Approval',
  approvers: ['approver1', 'approver2'],
  timeout: 24,
  status: 'pending'
}
```

## 🔧 Technical Details

### React Flow Integration
- **Custom Node Types**: StateNode and ApprovalNode components
- **Dynamic Updates**: Real-time state and evidence updates
- **Responsive Design**: Works on desktop and mobile
- **Performance**: Optimized for smooth animations

### State Management
- **React Hooks**: useState and useEffect for state management
- **Node Updates**: Dynamic node data updates
- **Edge Management**: Conditional edge rendering
- **Animation Control**: Play/pause/step functionality

### Styling
- **Tailwind CSS**: Utility-first CSS framework
- **Custom CSS**: React Flow specific styling
- **Responsive**: Mobile-friendly design
- **Accessibility**: High contrast and readable fonts

## 🚀 Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Static Hosting
```bash
# Build the project
npm run build

# Deploy build/ folder to your hosting service
# Examples: Netlify, Vercel, GitHub Pages, AWS S3
```

### Docker Deployment
```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🎯 Demo Best Practices

### For Executives
- **Focus on automation**: Show how manual work is reduced
- **Highlight compliance**: Emphasize audit trails and approvals
- **Show ROI**: Demonstrate time and cost savings
- **Security**: Point out PII redaction and secret masking

### For Technical Teams
- **Architecture**: Explain React Flow and state management
- **Integration**: Show how it connects to existing systems
- **Customization**: Demonstrate how to modify workflows
- **Performance**: Highlight smooth animations and responsiveness

### For Operations Teams
- **Process Flow**: Walk through each step in detail
- **Approval Gates**: Explain HITL mechanisms
- **Evidence Tracking**: Show compliance and audit capabilities
- **Error Handling**: Demonstrate blocked states and recovery

## 🎉 Next Steps

1. **Customize Workflows**: Modify states and transitions for your needs
2. **Add Integrations**: Connect to real ServiceNow, Jira, AWS APIs
3. **Enhance UI**: Add more visual elements and animations
4. **Deploy**: Host the demo for stakeholders to access
5. **Feedback**: Collect input and iterate on the design

---

**Ready to demo? Start with:**
```bash
cd visual-demo
npm install
npm start
```

**Open http://localhost:3000 and click Play!** 🚀

