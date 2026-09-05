; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 1.0) x))
(assert
 (>= 1.0 x))
(assert
 (not (and (and (distinct x 0.0) true))))
(check-sat)
