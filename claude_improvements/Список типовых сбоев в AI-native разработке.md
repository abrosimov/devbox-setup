- `MicrostepLiveBeatPass@Process` -- паттерн удержания внимания на одном проверяемом микрообъекте: строке, координате, finding, файле, trigger, source item.
* `QualityReviewPass@Process` -- паттерн проверки качества объекта, когда он заявлен как готовый, стабильный или достаточно улучшенный.
* `HLPackageDischargePass@Process` -- паттерн разрядки shared `H1..H15` и `L1..L12` по одному пункту, без "проверили в целом".
* `LexicalKindGovernancePass@Process` -- паттерн управления лексикой, kind-словами, метафорами маршрута, umbrella terms и точностью имён.
* `ReviewerE19GatePass@Process` -- паттерн reviewer-run `E.19` gate для admission, refresh, release, external-review или landing readiness.
* `DRRAdequacyPass@Process` -- паттерн проверки, что `DRR` годится как decision basis, а не просто имеет правильный заголовок.
* `AcceptedBasisCarryThroughPass@Process` -- паттерн протаскивания accepted intake, `DRR`, audit, returned finding или steward instruction в реальные правки.
* `ExternalReviewPacketReadinessPass@Process` -- паттерн готовности target/context packet, если external review уже выбран by value.
* `LandingRegressionPass@Process` -- паттерн проверки, что landing в монолит или canonical indexed source не потерял смысл, структуру, ссылки и discovery.
* `ProtocolResiduePass@Process` -- паттерн уборки process residue: что оставить current, что архивировать, что заменить указателем, что удалить.
* `PrelandingOntologicalHardeningPass@Process` -- паттерн онтологического hardening перед landing/review-facing gate: kind recovery, locus distribution, source-action discharge, readability.
* `HelperDomainModel@Process` -- pattern set для helper/domain model: baton, active handoff, current seam, dispatch projection, transport attempt, receipt, generated projection и regression invariants.
* `PlatformProcessChange@Process` -- паттерн изменения самого процесса, хелперов, транспорта, панели, fit functions и recovery-механики: сначала domain model и architecture, потом patch.
* ещё не написаны, но уже названы как кандидаты (backlog) -- `CampaignStartupAndDRROpening@Process`, `ReturnedFindingsIntakeAndRevalidation@Process`, `SafeWorkspaceEditAndRecovery@Process`.