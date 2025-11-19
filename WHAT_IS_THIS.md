# What is Prep?

**Prep is a commercial kitchen rental marketplace platform** that connects certified commercial kitchens with food entrepreneurs, handling regulatory compliance, booking orchestration, and payment processing.

## 🎯 The Problem We Solve

Food entrepreneurs (caterers, bakers, meal prep businesses) need access to certified commercial kitchens to legally produce food for sale. However:

- Finding compliant kitchens is difficult
- Multi-jurisdiction regulatory requirements are complex (FDA/FSMA, municipal codes)
- Booking management and payment processing is fragmented
- Certification verification is manual and time-consuming

## 💡 Our Solution

Prep automates the entire commercial kitchen rental workflow:

### For Kitchen Hosts
- **List your commercial kitchen** with automated compliance verification
- **Manage bookings** with conflict detection and availability calendar
- **Receive payments** via Stripe Connect with automated payouts
- **Stay compliant** with expiration tracking and renewal reminders

### For Food Entrepreneurs (Renters)
- **Find certified kitchens** that meet your regulatory requirements
- **Book instantly** with real-time availability
- **Pay securely** with built-in payment processing
- **Verify compliance** before booking with document verification

### For Administrators
- **Review certifications** with OCR document processing
- **Monitor compliance** across multiple jurisdictions
- **Audit activity** with comprehensive logging
- **Manage users** with role-based access control

## 🏗️ Technology Stack

### Backend
- **Python 3.11+** with FastAPI for async API gateway
- **TypeScript/Node.js** microservices (13 services) with Fastify
- **PostgreSQL 15** with PostGIS for geospatial queries
- **Redis 7** for caching and session management
- **Stripe Connect** for payment processing

### Frontend
- **Next.js 14** (App Router) with TypeScript
- **React** server/client components
- **TailwindCSS** for styling

### Infrastructure
- **Docker** + **Kubernetes** for containerization
- **GitHub Actions** (23 CI/CD workflows)
- **Prometheus** + **Grafana** for monitoring

## 📂 Repository Structure

```
Prep/
├── api/                    # Python FastAPI gateway
├── prepchef/              # TypeScript microservices
│   ├── services/          # 13 microservices (auth, booking, payments, etc.)
│   └── packages/          # Shared packages
├── apps/
│   ├── harborhomes/       # Next.js frontend
│   ├── federal_regulatory_service/
│   ├── city_regulatory_service/
│   └── vendor_verification/
├── prep/                  # Python shared libraries
│   ├── auth/             # JWT authentication
│   ├── compliance/       # Compliance engines
│   ├── payments/         # Stripe integration
│   └── models/           # SQLAlchemy models
├── tests/                # Test suites
├── migrations/           # Database migrations
├── .claude/             # Claude Code configuration
└── docs/                # Comprehensive documentation
```

## 🚀 Quick Start

### One-Command Setup
```bash
git clone https://github.com/PetrefiedThunder/Prep.git
cd Prep
make bootstrap    # Install deps, start services, run migrations
make health       # Verify all services are running
```

### Key Services
- **Frontend**: http://localhost:3001
- **API Gateway**: http://localhost:8000/docs
- **Node Backend**: http://localhost:3000/docs

## 📊 Current Status

**MVP Completion: ~25-35%** (as of November 2025)

| Component | Status | Completion |
|-----------|--------|------------|
| Database Schemas | ✅ | 90% |
| Authentication | ✅ | 70% |
| Federal Compliance | ✅ | 80% |
| City Compliance | ✅ | 75% |
| Booking Engine | ⚠️ | 40% |
| Payment Processing | ⚠️ | 50% |
| Admin Workflows | ⚠️ | 30% |
| Frontend | ❌ | 20% |
| E2E Flows | ❌ | 15% |

## 🔑 Key Features

### Implemented
- ✅ JWT authentication with database-backed validation
- ✅ Federal regulatory compliance tracking (FDA/FSMA)
- ✅ Multi-city compliance rules (8+ cities)
- ✅ OCR document processing for certifications
- ✅ Cost estimation for compliance requirements
- ✅ Booking conflict detection
- ✅ Stripe payment integration (Python service)
- ✅ RBAC with granular permissions
- ✅ Comprehensive audit logging

### In Progress
- 🔄 End-to-end booking flow
- 🔄 Frontend integration with real APIs
- 🔄 Real-time availability management
- 🔄 Automated compliance renewal notifications
- 🔄 Kitchen listing creation workflow

### Planned
- 📋 Mobile app
- 📋 Advanced analytics dashboard
- 📋 Multi-language support
- 📋 Integration with third-party kitchen management systems

## 🔒 Security

- **Zero HIGH severity vulnerabilities** (as of Nov 2025)
- JWT tokens with 15min access + 7-day refresh
- Database-backed session validation
- Input validation via Pydantic/Zod
- Rate limiting and throttling
- Comprehensive audit logging
- Regular dependency scanning (Dependabot)
- Pre-commit secret scanning (Gitleaks)

## 📚 Documentation

### Getting Started
- **[README.md](./README.md)** - Comprehensive project overview
- **[DEVELOPER_ONBOARDING.md](./DEVELOPER_ONBOARDING.md)** - New developer guide
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Contribution guidelines

### Technical Deep Dives
- **[Authentication Deep Dive](./docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md)** - Auth architecture
- **[MVP Implementation Plan](./docs/PREP_MVP_IMPLEMENTATION_PLAN.md)** - Development roadmap
- **[Architecture](./docs/architecture.md)** - System design

### Claude Code Configuration
- **[.claude/CONTEXT.md](./.claude/CONTEXT.md)** - Repository context for AI development
- **[CLAUDE.md](./CLAUDE.md)** - Quick reference for Claude Code

## 🤝 Contributing

We welcome contributions! To get started:

1. Read [CONTRIBUTING.md](./CONTRIBUTING.md)
2. Set up your development environment with `make bootstrap`
3. Check [open issues](https://github.com/PetrefiedThunder/Prep/issues)
4. Submit a PR following our standards

### Code Standards
- **Python**: Black formatting, mypy type checking, ruff linting
- **TypeScript**: Prettier formatting, strict type checking, ESLint
- **Commits**: Conventional Commits format
- **Tests**: 80%+ coverage target

## 🎯 Use Cases

### 1. Catering Company
A catering company needs a certified kitchen for a weekend event. They:
- Search for available kitchens in their city
- Filter by certification requirements (health permits, insurance)
- Book instantly with real-time availability
- Pay securely with credit card
- Receive booking confirmation with access details

### 2. Kitchen Owner
A restaurant owner has excess kitchen capacity during off-hours. They:
- List their kitchen with photos and amenities
- Upload certifications (health permit, insurance)
- Set availability and pricing
- Receive bookings automatically
- Get paid via direct deposit

### 3. Compliance Officer
A city compliance officer needs to verify all operating kitchens. They:
- View dashboard of all licensed kitchens
- See expiration dates for certifications
- Flag non-compliant operations
- Generate compliance reports

## 🌟 Why Prep?

- **Automated Compliance**: Stop worrying about regulatory requirements
- **Trusted Platform**: All kitchens are verified before listing
- **Seamless Booking**: Book instantly without email back-and-forth
- **Secure Payments**: Stripe-powered with buyer/seller protection
- **Multi-Jurisdiction**: Works across federal and municipal regulations
- **Developer-Friendly**: Well-documented, tested, and type-safe

## 📞 Support

- **Repository**: https://github.com/PetrefiedThunder/Prep
- **Issues**: https://github.com/PetrefiedThunder/Prep/issues
- **Security**: See [SECURITY.md](./SECURITY.md)
- **License**: MIT

---

**Built with ❤️ for the commercial kitchen sharing economy**

*Last Updated: November 2025*
