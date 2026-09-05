; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(declare-fun z () Real)
(declare-fun alpha () Real)
(assert
 (<= (- 4.0) x))
(assert
 (>= 4.0 x))
(assert
 (<= (- 4.0) z))
(assert
 (>= 4.0 z))
(assert
 (<= 0.0 alpha))
(assert
 (>= 1.0 alpha))
(check-sat)
