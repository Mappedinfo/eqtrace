; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 2.0) x))
(assert
 (>= 2.0 x))
(assert
 (let ((?x38 (^ x 2.0)))
(let ((?x24 (+ ?x38 1.0)))
(and (distinct ?x38 ?x24) true))))
(check-sat)
