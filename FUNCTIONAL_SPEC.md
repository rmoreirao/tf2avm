Here’s the **Functional Specification in Markdown** format for your Multi-Agent Terraform → AVM Migration system:

---

# Functional Specification: Multi-Agent Terraform → AVM Migration System

## 1. Overview

The system is a **Hierarchical Multi-Agent Architecture** that automates the migration of Terraform repositories into **Azure Verified Modules (AVM)**.

It accepts a repository (with multiple `.tf` files, variables, modules, and outputs) and produces either:

* A **fully converted AVM-based Terraform repo**, or
* A **detailed report** describing partial conversion results, issues, and next steps.

---

## 2. Multi-Agent Pattern

* **Hierarchical Orchestration**

  * One **Orchestrator Agent** manages execution.
  * Specialized **Worker Agents** handle scanning, knowledge retrieval, mapping, conversion, validation, and reporting.
  * Results are passed **bottom-up**, with Orchestrator merging outputs.

---

## 3. Agents Specification

### 3.1 Orchestrator Agent

**Goal**
Manage the overall workflow and coordinate other agents.

**Logic**

1. Receive repo path/URL.
2. Call Repo Scanner → AVM Knowledge → Mapping → Converter → Validator → Reviewer.
3. Decide final outcome (success vs. report).

**Input Format**

```json
{
  "repo_url": "https://dev.azure.com/org/project/_git/repo1"
}
```

**Output Format**

```json
{
  "status": "failed",
  "converted_repo_path": null,
  "report": "/output/repo1_report.md"
}
```

---

### 3.2 Repo Scanner Agent

**Goal**
Parse the **entire Terraform repository** into a structured manifest.

**Logic**

* Parse `.tf` files (resources, variables, outputs, modules).
* Build dependency graph.

**Input Format**

```json
{
  "repo_path": "/input/repo1"
}
```

**Output Format**

```json
{
  "files": [
    {
      "path": "main.tf",
      "resources": [
        {"type": "azurerm_virtual_network", "name": "vnet1"}
      ]
    },
    {
      "path": "network.tf",
      "resources": [
        {"type": "azurerm_subnet", "name": "subnet1"}
      ]
    }
  ],
  "variables": [
    {"name": "location", "default": "westeurope"}
  ],
  "outputs": [
    {"name": "vnet_id"}
  ],
  "providers": ["azurerm"],
  "terraform_version": "1.6.2"
}
```

---

### 3.3 AVM Knowledge Agent

**Goal**
Fetch the **latest AVM documentation and registry modules** for mapping.

**Input Format**

```json
{
  "query": ["azurerm_virtual_network", "azurerm_subnet"]
}
```

**Output Format**

```json
{
  "avm_index": [
    {
      "resource_type": "azurerm_virtual_network",
      "avm_module": "avm-res-network-virtualnetwork",
      "version": "1.2.3"
    },
    {
      "resource_type": "azurerm_subnet",
      "avm_module": "avm-res-network-subnet",
      "version": "2.0.1"
    }
  ]
}
```

---

### 3.4 Mapping Agent

**Goal**
Create **mappings from Terraform resources/modules → AVM equivalents**.

**Logic**

* Match resources and modules to AVM.
* Mark unmapped or partially mapped resources.

**Input Format**

```json
{
  "repo_manifest": {...},
  "avm_index": {...}
}
```

**Output Format**

```json
{
  "mappings": [
    {
      "original": "azurerm_virtual_network.vnet1",
      "mapped_to": "avm-res-network-virtualnetwork",
      "confidence": 0.95
    },
    {
      "original": "azurerm_subnet.subnet1",
      "mapped_to": "avm-res-network-subnet",
      "confidence": 0.90
    }
  ],
  "unmapped": []
}
```

---

### 3.5 Converter Agent

**Goal**
Convert **all Terraform files** into AVM-based Terraform.

**Logic**

* Replace resource blocks with AVM module calls.
* Rewrite variables and outputs accordingly.
* Generate converted repo structure.

**Input Format**

```json
{
  "repo_manifest": {...},
  "mappings": {...}
}
```

**Output Format**

```json
{
  "converted_repo_path": "/output/repo1_avm",
  "files_converted": [
    "main.tf",
    "network.tf",
    "variables.tf",
    "outputs.tf"
  ],
  "avm_mapping_file": "/output/repo1_avm/avm-mapping.json"
}
```

**Example Converted File**

```hcl
module "vnet" {
  source  = "Azure/avm-res-network-virtualnetwork/azurerm"
  version = "1.2.3"

  name                = "vnet1"
  address_space       = ["10.0.0.0/16"]
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
}
```

---

### 3.6 Validator Agent

**Goal**
Validate the converted repo.

**Logic**

* Run `terraform init && terraform validate`.
* Run `tflint` and `checkov`.

**Input Format**

```json
{
  "converted_repo_path": "/output/repo1_avm"
}
```

**Output Format**

```json
{
  "validation_status": "failed",
  "errors": [
    {
      "tool": "terraform",
      "message": "Missing required variable 'dns_servers'."
    }
  ],
  "warnings": []
}
```

---

### 3.7 Reviewer Agent

**Goal**
Generate a **conversion report**.

**Logic**

* If conversion fully successful → summarize migrated resources and repo path.
* If partial → list errors, unmapped resources, and manual steps.

**Input Format**

```json
{
  "validation_status": "failed",
  "errors": [...],
  "warnings": [...],
  "mappings": [...]
}
```

**Output Format (Markdown Report)**

```markdown
# Conversion Report: repo1

## ✅ Converted Files
- main.tf → AVM
- network.tf → AVM
- variables.tf → AVM
- outputs.tf → AVM

## ✅ Successful Mappings
- azurerm_virtual_network → avm-res-network-virtualnetwork
- azurerm_subnet → avm-res-network-subnet

## ⚠️ Issues Found
- Missing required variable `dns_servers` in AVM vnet module.

## 🔧 Next Steps
- Add `dns_servers` input manually before deployment.

## 📂 Converted Repo Location
`/output/repo1_avm`
```

---

## 4. Expected Outcomes

* **Success Path**: Converted repo with AVM modules and validation passed.
* **Failure Path**: Conversion report with issues, unmapped resources, and guidance for manual intervention.

---

Do you want me to also add a **visual architecture diagram** (ASCII/Markdown style) to complement this spec? That way it’s easier for engineers to see the orchestration flow at a glance.
