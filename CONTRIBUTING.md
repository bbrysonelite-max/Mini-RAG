# Contributing to Mini-RAG

## Git Workflow

### Branch Strategy
- `main` - Production-ready code (stable releases)
- `develop` - Development branch (integration branch)
- `feature/*` - New features
- `fix/*` - Bug fixes
- `security/*` - Security-related changes

### Workflow
1. Create a feature branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: description of your feature"
   ```

3. Push and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

4. After review, merge to `develop`, then to `main` for releases

### Commit Message Format
- `feat:` - New feature
- `fix:` - Bug fix
- `security:` - Security fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `test:` - Tests
- `chore:` - Maintenance

Example: `feat: add user authentication system`

